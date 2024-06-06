use poise::serenity_prelude as serenity;
use poise::CreateReply;
use rand::seq::IteratorRandom;
use rand::thread_rng;

use crate::data::neofetch;
use crate::{Context, Result};

use super::Cog;

pub fn cog() -> Cog {
    Cog::new(vec![neofetch()], "Gadgets".to_string())
}

#[poise::command(prefix_command, slash_command)]
async fn neofetch(ctx: Context<'_>, #[rest] distro: String) -> Result<()> {
    let distro = if distro.is_empty() {
        neofetch::variants()
            .keys()
            .choose(&mut thread_rng())
            .unwrap()
    } else {
        neofetch::patterns()
            .iter()
            .find(|(pattern, _, _)| pattern.is_match(&distro))
            .ok_or("err")?
            .1
    };
    let logo = neofetch::logos()[distro];
    let embed = serenity::CreateEmbed::new()
        .description(format!("```ansi\n{logo}\n```"))
        .footer(serenity::CreateEmbedFooter::new(
            "Neofetch data last updated:",
        ))
        .timestamp(serenity::Timestamp::from_unix_timestamp(
            neofetch::LAST_UPDATED_POSIX,
        )?);
    ctx.send(CreateReply::default().embed(embed)).await?;
    Ok(())
}
