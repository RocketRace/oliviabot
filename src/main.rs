mod cogs;
mod database;
mod errors;
mod state;
mod util;

use std::any::Any;

use errors::global_error_handler;
use poise::{
    builtins,
    serenity_prelude::{self as serenity, CacheHttp, ExecuteWebhook},
    Framework, FrameworkOptions,
};
use serde::{de::Error as _, Deserialize, Deserializer};
use state::Data;
use tokio::{
    select,
    signal::unix::{signal, SignalKind},
    sync::watch,
};
use tracing::{error, info};

// Common types
pub type Error = Box<dyn std::error::Error + Send + Sync>;
pub type Context<'a> = poise::Context<'a, Data, Error>;
pub type Result<T, E = Error> = std::result::Result<T, E>;
pub type Commands = Vec<poise::Command<Data, Error>>;

#[derive(Deserialize, Debug, Clone)]
pub struct Config {
    #[serde(flatten)]
    pub secrets: Secrets,
    pub database_url: String,
    #[serde(deserialize_with = "hex_color")]
    pub default_embed_color: serenity::Color,
}

#[derive(Deserialize, Debug, Clone)]
pub struct Secrets {
    pub bot_token: String,
    pub webhook_url: String,
}

pub struct Spanned {
    pub file: &'static str,
    pub line: u32,
    pub inner: Box<dyn Any + Send + Sync + 'static>,
}

fn hex_color<'de, D: Deserializer<'de>>(d: D) -> std::result::Result<serenity::Color, D::Error> {
    let s: String = Deserialize::deserialize(d)?;
    let result = u32::from_str_radix(&s, 16).map_err(D::Error::custom)?;
    Ok(serenity::Colour(result))
}

#[tokio::main]
async fn main() -> Result<()> {
    let dev = std::env::var("DEV").is_ok();
    if dev {
        dotenvy::from_filename(".dev.env")?;
    } else {
        dotenvy::dotenv()?;
    }

    let config = envy::from_env::<Config>()?;
    let token = config.secrets.bot_token.clone();

    tracing_subscriber::fmt().compact().init();

    if dev {
        info!("Starting bot in development configuration")
    } else {
        info!("Starting bot using main configuration")
    }

    let intents = serenity::GatewayIntents::non_privileged()
        | serenity::GatewayIntents::MESSAGE_CONTENT
        | serenity::GatewayIntents::GUILD_PRESENCES;

    let framework = Framework::builder()
        .options(FrameworkOptions {
            commands: cogs::commands(),
            on_error: |e| Box::pin(global_error_handler(e)),
            ..Default::default()
        })
        .setup(|ctx, ready, framework| {
            info!("Logged in as {} (ID: {})", ready.user.name, ready.user.id);
            Box::pin(async move {
                builtins::register_globally(ctx, &framework.options().commands).await?;
                let data = Data::from_config(&config).await;

                let webhook = ctx
                    .http()
                    .get_webhook_from_url(&config.secrets.webhook_url)
                    .await?;

                webhook
                    .execute(
                        ctx.http(),
                        true,
                        ExecuteWebhook::new().content(format!("Logged in as {}!", ready.user.name)),
                    )
                    .await?;

                data
            })
        })
        .build();

    let mut client = serenity::ClientBuilder::new(token, intents)
        .framework(framework)
        .await
        .map_err(|e| format!("Failed to create client: {e}"))?;

    let shard_manager = client.shard_manager.clone();

    let (shutdown_tx, mut shutdown_rx) = watch::channel(());
    let error_shutdown_tx = shutdown_tx.clone();

    let signal_trap = tokio::spawn(async move {
        let mut sigterm = signal(SignalKind::terminate()).unwrap();
        let mut sigint = signal(SignalKind::interrupt()).unwrap();
        select! {
            _ = sigterm.recv() => info!("Recieved SIGTERM"),
            _ = sigint.recv() => info!("Recieved SIGINT"),
        };
        shutdown_tx.clone().send(()).unwrap();
    });

    tokio::spawn(async move {
        let _ = shutdown_rx.changed().await;
        shard_manager.shutdown_all().await;
    });

    if let Err(e) = client.start().await {
        error!("Error running the client: {e}");
        // ensures that the shutdown future completes gracefully
        error_shutdown_tx.send(()).unwrap();
    };
    signal_trap.abort();
    Ok(())
}
