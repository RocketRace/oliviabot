mod admin;
mod state;
mod util;

use admin::debug;
use poise::{builtins, serenity_prelude as serenity, Framework, FrameworkOptions};
use serde::Deserialize;
use state::Data;

// Common types
pub type Error = Box<dyn std::error::Error + Send + Sync>;
pub type Context<'a> = poise::Context<'a, Data, Error>;
pub type Result<T> = std::result::Result<T, Error>;

#[derive(Deserialize)]
struct Config {
    token: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv()?;
    let config = envy::from_env::<Config>()?;

    tracing_subscriber::fmt().compact().init();

    let intents =
        serenity::GatewayIntents::non_privileged() | serenity::GatewayIntents::MESSAGE_CONTENT;

    let framework = Framework::builder()
        .options(FrameworkOptions {
            commands: vec![debug()],
            ..Default::default()
        })
        .setup(|ctx, _ready, framework| {
            Box::pin(async move {
                builtins::register_globally(ctx, &framework.options().commands).await?;
                Data::new()
            })
        })
        .build();

    serenity::ClientBuilder::new(config.token, intents)
        .framework(framework)
        .await?
        .start()
        .await?;

    Ok(())
}
