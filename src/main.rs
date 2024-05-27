use chrono::{Days, TimeDelta};
use poise::{builtins, serenity_prelude as serenity, CreateReply, Framework, FrameworkOptions};
use serde::Deserialize;

// Shared state
#[derive(Default)]
struct Data {}

// Common types
type Error = Box<dyn std::error::Error + Send + Sync>;
type Context<'a> = poise::Context<'a, Data, Error>;
type Result<T> = std::result::Result<T, Error>;

fn format_delta(start: serenity::Timestamp, end: serenity::Timestamp) -> Result<String> {
    Ok(format!("{:?}", end.signed_duration_since(*start).to_std()?))
}

/// Shows debug information about the bot.
#[poise::command(prefix_command)]
async fn debug(ctx: Context<'_>) -> Result<()> {
    let received = ctx.created_at();
    let now = serenity::Timestamp::now();

    let make_ping = |sent: Option<serenity::Timestamp>| -> Result<String> {
        Ok(format!(
            "Discord -> Bot: {}\nBot -> Discord: {}",
            format_delta(received, now)?,
            match sent {
                Some(sent) => format_delta(now, sent)?,
                None => "...".into(),
            }
        ))
    };

    let base_embed = serenity::CreateEmbed::new()
        .title("Debug statistics")
        .field("Ping", make_ping(None)?, true);

    let msg = ctx
        .say(format!(
            "Discord -> Bot: {}\nBot -> Discord: ...",
            format_delta(received, now)?
        ))
        .await?;
    let sent = msg.message().await?.timestamp;

    msg.edit(
        ctx,
        CreateReply::default().content(
            msg.message()
                .await?
                .content
                .replace("...", &format_delta(now, sent)?),
        ),
    )
    .await?;
    Ok(())
}

#[derive(Deserialize)]
struct Config {
    token: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv()?;
    let config = envy::from_env::<Config>()?;

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
                Ok(Data::default())
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
