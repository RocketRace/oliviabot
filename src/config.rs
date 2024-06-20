use std::sync::LazyLock;

use anyhow::Context;
use poise::serenity_prelude as serenity;
use serde::{de::Error, Deserialize, Deserializer};

#[derive(Deserialize, Debug, Clone)]
pub struct Config {
    pub dev: bool,
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

fn hex_color<'de, D: Deserializer<'de>>(d: D) -> std::result::Result<serenity::Color, D::Error> {
    let s: String = Deserialize::deserialize(d)?;
    let result = u32::from_str_radix(&s, 16).map_err(D::Error::custom)?;
    Ok(serenity::Colour(result))
}

pub static CONFIG: LazyLock<Config> = LazyLock::new(|| {
    let dev = std::env::var("DEV").is_ok();
    if dev {
        dotenvy::from_filename(".dev.env").expect(".dev.env should exist");
    } else {
        dotenvy::dotenv().expect(".env should exist");
    }

    envy::from_env::<Config>()
        .context("Configuration is invalid")
        .unwrap()
});
