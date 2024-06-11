use anyhow::Context as _;
use poise::serenity_prelude as serenity;
use poise::CreateReply;
use rand::seq::SliceRandom;
use rand::thread_rng;
use rusqlite::params;

use crate::{Context, Result};

use super::Cog;

pub fn cog() -> Cog {
    Cog::new(vec![neofetch()], "Gadgets".to_string())
}

#[poise::command(prefix_command, slash_command)]
async fn neofetch(
    ctx: Context<'_>,
    #[flag] mobile: bool,
    #[rest] distro: Option<String>,
) -> Result<()> {
    let mobile = mobile
        || if let Some(serenity::Presence {
            client_status:
                Some(serenity::ClientStatus {
                    mobile: Some(mobile_status),
                    ..
                }),
            status,
            ..
        }) = ctx
            .guild()
            .and_then(|guild| guild.presences.get(&ctx.author().id).cloned())
        {
            status == mobile_status
        } else {
            false
        };
    let conn = ctx.data().db.get()?;

    let choices = {
        let mut stmt = conn
            .prepare(
                "SELECT distro, logo FROM neofetch
                WHERE (?1 IS NULL OR ?1 REGEXP pattern) AND (?2 IS NULL OR mobile_width = ?2)",
            )
            .context("Failed to prepare SQL statement")?;

        // the internal csv table represents true/false as strings
        let params = params![distro, mobile.then_some("1")];

        let rows = stmt
            .query_map(params, |row| Ok((row.get(0)?, row.get(1)?)))
            .context("Failed to execute SQL")?;

        let mut choices: Vec<(String, String)> = vec![];
        for row in rows {
            choices.push(row?);
        }
        choices
    };

    let neofetch_updated = ctx.data().neofetch_updated;

    let Some((distro, logo)) = choices.choose(&mut thread_rng()) else {
        return Err("No such distro found")?;
    };

    let embed = serenity::CreateEmbed::new()
        .description(format!("```ansi\n{logo}\n```"))
        .footer(serenity::CreateEmbedFooter::new(
            "Neofetch data last updated:",
        ))
        .field(
            format!(
                "{}@{}",
                ctx.author().name,
                ctx.channel_id().name(ctx).await?
            ),
            format!(
                "```\n\
                OS: {distro}\n\
                Host: Discord\n\
                ```"
            ),
            false,
        )
        .timestamp(neofetch_updated);

    ctx.send(CreateReply::default().embed(embed)).await?;

    Ok(())
}
