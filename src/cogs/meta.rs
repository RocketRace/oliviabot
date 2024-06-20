use crate::{Context, Spanned};
use chrono::{DateTime, FixedOffset, Offset, Utc};
use poise::{
    builtins::autocomplete_command, samples::HelpConfiguration, serenity_prelude as serenity,
    CreateReply,
};
use span_derive::inject_span;

use super::Cog;

pub fn cog() -> Cog {
    Cog::new(vec![help(), debug(), source()], "Meta".to_string())
}

fn format_duration(start: serenity::Timestamp, end: serenity::Timestamp) -> anyhow::Result<String> {
    Ok(format!("{:?}", end.signed_duration_since(*start).to_std()?))
}

fn format_ping(
    received: serenity::Timestamp,
    now: serenity::Timestamp,
    sent: Option<serenity::Timestamp>,
    gateway: std::time::Duration,
) -> anyhow::Result<String> {
    Ok(format!(
        "Discord -> Bot: {}\nBot -> Discord: {}\nGateway: {:?}",
        format_duration(received, now)?,
        match sent {
            Some(sent) => format_duration(now, sent)?,
            None => "...".into(),
        },
        gateway
    ))
}

const MAX_COMMITS_SHOWN: usize = 4;
const SHORT_SHA_LENGTH: usize = 6;
const MAX_COMMIT_MESSAGE_LENGTH: usize = 50;

/// Shows debug information about the bot.
#[inject_span]
#[poise::command(prefix_command)]
async fn debug(ctx: Context<'_>) -> anyhow::Result<()> {
    let received = ctx.created_at();
    let now = serenity::Timestamp::now();

    let commits = if let Some(repo) = &ctx.data().repo {
        let handle = repo.handle.lock().expect("mutex is no longer valid");
        let mut walk = handle.revwalk()?;
        walk.push_head()?;
        walk.set_sorting(git2::Sort::TOPOLOGICAL)?;
        let tmp = walk.take(MAX_COMMITS_SHOWN).try_fold(
            String::new(),
            |acc, rev| -> anyhow::Result<String> {
                let oid = rev?;
                let commit = handle.find_commit(oid)?;
                let msg = commit.message().unwrap_or("<invalid UTF-8>");

                let seconds = commit.time().seconds();
                let offset_minutes = commit.time().offset_minutes();

                let dt = DateTime::from_timestamp(seconds, 0)
                    .unwrap_or_default()
                    .with_timezone(
                        &FixedOffset::east_opt(offset_minutes * 60).unwrap_or(Utc.fix()),
                    );

                let timestamp = serenity::utils::FormattedTimestamp::new(
                    serenity::Timestamp::from(dt),
                    Some(serenity::FormattedTimestampStyle::RelativeTime),
                );

                let line = format!(
                    "\n[`{}`]({}/commit/{}) {}: {}",
                    &oid.to_string()[..SHORT_SHA_LENGTH],
                    repo.url,
                    &oid.to_string(),
                    timestamp,
                    msg.trim()
                        .chars()
                        .take(MAX_COMMIT_MESSAGE_LENGTH)
                        .collect::<String>()
                );

                Ok(acc + &line)
            },
        )?;
        #[allow(clippy::let_and_return)]
        // https://github.com/rust-lang/rust-clippy/issues/12831
        tmp
    } else {
        "*No Git repository found*".into()
    };

    let base_embed = serenity::CreateEmbed::new()
        .color(ctx.data().config.default_embed_color)
        .title("Recent commits")
        .description(commits)
        .field(
            "Stats",
            format!("{} servers\n", ctx.cache().guilds().len()),
            true,
        );

    let gateway = ctx.ping().await;

    // separate start and end embeds for pre- and post- edit
    let start_embed =
        base_embed
            .clone()
            .field("Ping", format_ping(received, now, None, gateway)?, true);

    let msg = ctx.send(CreateReply::default().embed(start_embed)).await?;

    let sent = msg.message().await?.timestamp;

    let end_embed = base_embed.field(
        "Ping",
        format_ping(received, now, Some(sent), gateway)?,
        true,
    );

    msg.edit(ctx, CreateReply::default().embed(end_embed))
        .await?;
    Ok(())
}

/// Get help on the bot or a command
#[inject_span]
#[poise::command(prefix_command, slash_command)]
async fn help(
    ctx: Context<'_>,
    #[description = "Command to show help about"]
    #[autocomplete = "autocomplete_command"]
    command: Option<String>,
) -> anyhow::Result<()> {
    let config = HelpConfiguration::default();
    poise::builtins::help(ctx, command.as_deref(), config).await?;
    Ok(())
}

/// Fetch the source code of a command
#[inject_span]
#[poise::command(prefix_command, slash_command)]
async fn source(
    ctx: Context<'_>,
    #[description = "Command to show the source of"]
    #[autocomplete = "autocomplete_command"]
    command: String,
) -> anyhow::Result<()> {
    if let Some(span) = ctx
        .framework()
        .options()
        .commands
        .iter()
        .find(|cmd| cmd.name == command || cmd.aliases.contains(&command))
        .and_then(|resolved| resolved.custom_data.downcast_ref::<Spanned>())
    {
        ctx.say(format!(
            "Command `{command}` is defined in [`{}`, line {}](<https://github.com/RocketRace/oliviabot/blob/main/{}#L{}>)",
            span.file, span.line, span.file, span.line
        ))
        .await?;
    } else {
        ctx.say(format!("Command `{command}` not found")).await?;
    }
    Ok(())
}
