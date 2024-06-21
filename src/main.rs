mod cogs;
mod config;
mod database;
mod errors;
mod state;
mod util;

use std::any::Any;

use anyhow::Context as _;
use poise::{
    builtins,
    serenity_prelude::{self as serenity, CacheHttp, ExecuteWebhook},
    Framework, FrameworkOptions,
};
use tokio::{
    select,
    signal::unix::{signal, SignalKind},
    sync::watch,
};
use tracing::{error, info};

use crate::config::CONFIG;
use crate::errors::global_error_handler;
use crate::state::Data;

// Common types
pub type Context<'a> = poise::Context<'a, Data, anyhow::Error>;
pub type Commands = Vec<poise::Command<Data, anyhow::Error>>;

pub struct Spanned {
    pub file: &'static str,
    pub line: u32,
    pub inner: Box<dyn Any + Send + Sync + 'static>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let token = CONFIG.secrets.bot_token.clone();

    tracing_subscriber::fmt().compact().init();

    if CONFIG.is_dev() {
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
                let data = Data::from_config(&CONFIG).await;

                std::fs::write(".build-success", "")?;

                let webhook = ctx
                    .http()
                    .get_webhook_from_url(&CONFIG.secrets.webhook_url)
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
        .context("Failed to create client")?;

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
