use anyhow::anyhow;
use anyhow::Context as _;
use poise::serenity_prelude as serenity;
use poise::CreateReply;
use rand::seq::SliceRandom;
use rand::thread_rng;
use rusqlite::params;
use span_derive::inject_span;
use tracing::warn;

use crate::util::author_is_mobile;
use crate::{Context, Result, Spanned};

use super::Cog;

pub fn cog() -> Cog {
    Cog::new(vec![neofetch()], "Gadgets".to_string())
}

async fn autocomplete_neofetch(ctx: Context<'_>, partial: &str) -> Vec<String> {
    let inner = || -> Result<Vec<String>> {
        let conn = ctx.data().db.get()?;
        let mut stmt = conn
            .prepare(
                "SELECT DISTINCT distro FROM neofetch
                WHERE instr(lower(distro), lower(?1))
                ORDER BY distro
                LIMIT 25",
            )
            .context("Failed to prepare SQL statement")?;
        let mut output: Vec<String> = vec![];
        for row in stmt.query_map([partial], |row| row.get(0))? {
            output.push(row?);
        }
        Ok(output)
    };
    inner().unwrap_or_else(|e| {
        warn!("Error in autocomplete: {e:?}");
        vec![]
    })
}

/// Generate a neofetch command output
#[inject_span]
#[poise::command(prefix_command, slash_command)]
async fn neofetch(
    ctx: Context<'_>,
    #[flag] mobile: bool,
    #[autocomplete = "autocomplete_neofetch"]
    #[rest]
    distro: Option<String>,
) -> Result<()> {
    let mobile = mobile || author_is_mobile(ctx);
    let conn = ctx.data().db.get()?;

    let choices = {
        let mut stmt = if mobile {
            conn.prepare(
                "SELECT distro, logo, color_index, color_rgb FROM neofetch
                WHERE mobile_width IS TRUE 
                AND (?1 IS NULL OR lower(?1) REGEXP pattern OR concat(lower(?1), suffix) REGEXP pattern)
                ",
            )
            .context("Failed to prepare SQL statement")?
        } else {
            conn.prepare(
                "SELECT distro, logo, color_index, color_rgb FROM neofetch
                WHERE ?1 IS NULL OR lower(?1) REGEXP pattern",
            )
            .context("Failed to prepare SQL statement")?
        };

        let rows = stmt
            .query_map(params![distro], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
            })
            .context("Failed to execute SQL query")?;

        let mut choices: Vec<(String, String, String, String)> = vec![];
        for row in rows {
            choices.push(row?);
        }
        choices
    };

    let Some((distro, logo, color_index, color_rgb)) = choices.choose(&mut thread_rng()) else {
        return Err(match distro {
            Some(query) if mobile => {
                anyhow!("No mobile-width distro icons found matching query '{query}'")
            }
            Some(query) => anyhow!("No distros found matching query '{query}'"),
            None => anyhow!("No distros found."),
        })?;
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
        .timestamp(ctx.data().neofetch_updated)
        .color(serenity::Colour::from_rgb(r, g, b));

    ctx.send(CreateReply::default().embed(embed)).await?;

    Ok(())
}
