mod cogs;
mod data;
mod state;
mod util;

use poise::{
    builtins,
    serenity_prelude::{self as serenity},
    Framework, FrameworkOptions,
};
use serde::{de::Error as _, Deserialize, Deserializer};
use state::Data;
use tokio::{
    select,
    signal::unix::{signal, SignalKind},
    sync::watch,
};
use tracing::info;

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
}

fn hex_color<'de, D: Deserializer<'de>>(d: D) -> std::result::Result<serenity::Color, D::Error> {
    let s: String = Deserialize::deserialize(d)?;
    let result = u32::from_str_radix(&s, 16).map_err(D::Error::custom)?;
    Ok(serenity::Colour(result))
}

#[tokio::main]
async fn main() -> Result<()> {
    let (stop_tx, mut stop_rx) = watch::channel(());
    tokio::spawn(async move {
        let mut sigterm = signal(SignalKind::terminate()).unwrap();
        let mut sigint = signal(SignalKind::interrupt()).unwrap();
        loop {
            select! {
                _ = sigterm.recv() => info!("Recieved SIGTERM"),
                _ = sigint.recv() => info!("Recieved SIGINT"),
            };
            stop_tx.send(()).unwrap();
        }
    });

    let dev = std::env::var("DEV").is_ok();
    if dev {
        dotenvy::from_filename("dev.env")?;
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
            ..Default::default()
        })
        .setup(|ctx, ready, framework| {
            info!("Logged in as {} (ID: {})", ready.user.name, ready.user.id);
            Box::pin(async move {
                builtins::register_globally(ctx, &framework.options().commands).await?;
                Data::from_config(&config).await
            })
        })
        .build();

    let mut client = serenity::ClientBuilder::new(token, intents)
        .framework(framework)
        .await?;

    let shard_manager = client.shard_manager.clone();
    tokio::spawn(async move {
        if let Err(e) = stop_rx.changed().await {
            println!("Error receiving shutdown signal: {e}")
        };
        shard_manager.shutdown_all().await;
    });

    client.start().await?;
    Ok(())
}
