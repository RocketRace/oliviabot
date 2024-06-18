use poise::serenity_prelude as serenity;

use crate::Context;

pub fn author_is_mobile(ctx: Context<'_>) -> bool {
    if let Some(serenity::Presence {
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
    }
}
