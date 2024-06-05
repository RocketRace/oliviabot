use poise::serenity_prelude::CreateEmbed;
use poise::CreateReply;

use crate::data::neofetch;
use crate::{Context, Result};

use super::Cog;

pub fn cog() -> Cog {
    Cog::new(vec![neofetch()], "Gadgets".to_string())
}

#[poise::command(prefix_command, slash_command)]
async fn neofetch(ctx: Context<'_>, distro: Option<String>) -> Result<()> {
    let distro = distro.unwrap_or("Xenia".into());
    let xenia = neofetch::logos()[distro.as_str()].replace('`', "`\u{200b}");
    let embed = CreateEmbed::new().description(format!("```ansi\n{xenia}\n```"));
    ctx.send(CreateReply::default().embed(embed)).await?;
    Ok(())
}
