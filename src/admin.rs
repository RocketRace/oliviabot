use crate::{Context, Result};
use chrono::{DateTime, FixedOffset, Offset, Utc};
use chrono_humanize::{Accuracy, HumanTime, Tense};
use poise::{serenity_prelude as serenity, CreateReply};

fn format_duration(start: serenity::Timestamp, end: serenity::Timestamp) -> Result<String> {
    Ok(format!("{:?}", end.signed_duration_since(*start).to_std()?))
}

fn format_ping(
    received: serenity::Timestamp,
    now: serenity::Timestamp,
    sent: Option<serenity::Timestamp>,
) -> Result<String> {
    Ok(format!(
        "Discord -> Bot: {}\nBot -> Discord: {}",
        format_duration(received, now)?,
        match sent {
            Some(sent) => format_duration(now, sent)?,
            None => "...".into(),
        }
    ))
}

const MAX_COMMITS_SHOWN: usize = 6;

/// Shows debug information about the bot.
#[poise::command(prefix_command)]
pub async fn debug(ctx: Context<'_>) -> Result<()> {
    let received = ctx.created_at();
    let now = serenity::Timestamp::now();

    let commits = if let Some(repo) = &ctx.data().repo {
        let handle = repo.handle.lock().unwrap();
        let mut walk = handle.revwalk()?;
        walk.push_head()?;
        walk.set_sorting(git2::Sort::TOPOLOGICAL)?;
        let tmp =
            walk.take(MAX_COMMITS_SHOWN)
                .try_fold(String::new(), |acc, rev| -> Result<String> {
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

                    let timestamp = HumanTime::from(dt).to_text_en(Accuracy::Rough, Tense::Past);

                    let line = format!("\n[`{:06}`]({}) {}: {:16}", oid, repo.url, timestamp, msg);

                    Ok(acc + &line)
                })?;
        tmp
    } else {
        "*No Git repository found*".into()
    };

    let base_embed = serenity::CreateEmbed::new()
        .title("Recent commits")
        .description(commits);

    let start_embed = base_embed
        .clone()
        .field("Ping", format_ping(received, now, None)?, true);

    let msg = ctx.send(CreateReply::default().embed(start_embed)).await?;

    let sent = msg.message().await?.timestamp;

    let end_embed = base_embed.field("Ping", format_ping(received, now, Some(sent))?, true);

    msg.edit(ctx, CreateReply::default().embed(end_embed))
        .await?;
    Ok(())
}
