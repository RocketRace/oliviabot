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
                "SELECT distro, logo, color_index, color_rgb FROM neofetch
                WHERE (?1 IS NULL OR ?1 REGEXP pattern) AND (?2 IS NULL OR mobile_width = ?2)",
            )
            .context("Failed to prepare SQL statement")?;

        // the internal csv table represents true/false as strings
        let params = params![distro, mobile.then_some("1")];

        let rows = stmt
            .query_map(params, |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
            })
            .context("Failed to execute SQL")?;

        let mut choices: Vec<(String, String, String, String)> = vec![];
        for row in rows {
            choices.push(row?);
        }
        choices
    };

    let neofetch_updated = ctx.data().neofetch_updated;

    let Some((distro, logo, color_index, color_rgb)) = choices.choose(&mut thread_rng()) else {
        return Err("No such distro found")?;
    };

    let r = u8::from_str_radix(&color_rgb[0..2], 16)?;
    let g = u8::from_str_radix(&color_rgb[2..4], 16)?;
    let b = u8::from_str_radix(&color_rgb[4..6], 16)?;

    let accent = format!("\x1b[{color_index}m");
    let normal = "\x1b[0m";

    let embed = serenity::CreateEmbed::new()
        .description(format!(
            "```ansi\n\
            {logo}\n\
            ```\n\
            ```ansi\n\
            {accent}{}@{}{normal}\n\
            {accent}OS:{normal} {distro}\n\
            {accent}Host:{normal} Discord\n\
            ```",
            ctx.author().name,
            ctx.channel_id().name(ctx).await?
        ))
        .footer(serenity::CreateEmbedFooter::new(
            "Neofetch data last updated:",
        ))
        .timestamp(neofetch_updated)
        .color(serenity::Colour::from_rgb(r, g, b));

    ctx.send(CreateReply::default().embed(embed)).await?;

    Ok(())
}
