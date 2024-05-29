mod admin;
mod state;
mod util;

use admin::debug;
use poise::{builtins, serenity_prelude as serenity, Framework, FrameworkOptions};
use serde::{de::Error as _, Deserialize, Deserializer};
use state::Data;
use tracing::info;

// Common types
pub type Error = Box<dyn std::error::Error + Send + Sync>;
pub type Context<'a> = poise::Context<'a, Data, Error>;
pub type Result<T> = std::result::Result<T, Error>;

#[derive(Deserialize, Debug, Clone)]
struct Config {
    token: String,
    #[serde(flatten)]
    public: PublicConfig,
}

fn hex_color<'de, D: Deserializer<'de>>(d: D) -> std::result::Result<serenity::Color, D::Error> {
    let s: String = Deserialize::deserialize(d)?;
    let result = u32::from_str_radix(&s, 16).map_err(D::Error::custom)?;
    Ok(serenity::Colour(result))
}

#[derive(Debug, Clone, Deserialize)]
pub struct PublicConfig {
    pub database_url: String,
    #[serde(deserialize_with = "hex_color")]
    pub default_embed_color: serenity::Color,
}

#[tokio::main]
async fn main() -> Result<()> {
    let dev = std::env::var("DEV").is_ok();
    if dev {
        dotenvy::from_filename("dev.env")?;
    } else {
        dotenvy::dotenv()?;
    }

    let Config { token, public } = envy::from_env::<Config>()?;

    tracing_subscriber::fmt().compact().init();

    if dev {
        info!("Starting bot in development configuration")
    } else {
        info!("Starting bot using main configuration")
    }

    let intents =
        serenity::GatewayIntents::non_privileged() | serenity::GatewayIntents::MESSAGE_CONTENT;

    let framework = Framework::builder()
        .options(FrameworkOptions {
            commands: vec![debug()],
            ..Default::default()
        })
        .setup(|ctx, ready, framework| {
            info!("Logged in as {} (ID: {})", ready.user.name, ready.user.id);
            Box::pin(async move {
                builtins::register_globally(ctx, &framework.options().commands).await?;
                Data::from_config(&public).await
            })
        })
        .build();

    let mut client = serenity::ClientBuilder::new(token, intents)
        .framework(framework)
        .await?;

    let shard_manager = client.shard_manager.clone();
    tokio::spawn(async move {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to register ctrl-c handler");

        shard_manager.shutdown_all().await;
    });

    client.start().await?;
    Ok(())
}
