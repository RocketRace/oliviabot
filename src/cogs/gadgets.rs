use std::time::Duration;

use poise::serenity_prelude as serenity;
use poise::serenity_prelude::OnlineStatus;
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
async fn neofetch(ctx: Context<'_>, #[rest] distro: Option<String>) -> Result<()> {
    let mobile = if let Some(serenity::Presence {
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
    let distro = if let Some(distro) = distro {
        neofetch::patterns()
            .iter()
            .find(|(pattern, _, _)| pattern.is_match(&distro))
            .ok_or(format!("Distro '{}' not found", distro))?
            .1
    } else {
        neofetch::variants()
            .keys()
            .choose(&mut thread_rng())
            .unwrap()
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

    let id = ctx.id();
    let button = serenity::CreateButton::new(format!("{id}"))
        .label("Mobile")
        .style(serenity::ButtonStyle::Secondary);

    let component = serenity::CreateActionRow::Buttons(vec![button]);

    ctx.send(
        CreateReply::default()
            .embed(embed)
            .components(vec![component]),
    )
    .await?;

    while let Some(interaction) = serenity::ComponentInteractionCollector::new(ctx)
        .author_id(ctx.author().id)
        .channel_id(ctx.channel_id())
        .timeout(Duration::from_secs(120))
        .filter(move |mci| mci.data.custom_id == id.to_string())
        .await
    {
        let _msg = interaction.message.clone();
        // msg.edit(ctx).await?;

        interaction
            .create_response(ctx, serenity::CreateInteractionResponse::Acknowledge)
            .await?;
    }

    Ok(())
}
