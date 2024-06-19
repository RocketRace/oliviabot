use poise::{
    builtins,
    serenity_prelude::{CreateAttachment, ExecuteWebhook},
    FrameworkError,
};
use tracing::error;

use crate::{state::Data, Context, Error, Result};

async fn webhook_alert(ctx: Context<'_>, e: &FrameworkError<'_, Data, Error>) -> Result<()> {
    let url = &ctx.data().config.secrets.webhook_url;
    let webhook = ctx.http().get_webhook_from_url(url).await?;

    let debug_output = format!("{e:?}");
    let payload = ExecuteWebhook::new()
        .content(format!("{e}"))
        .add_file(CreateAttachment::bytes(debug_output, "full_error.txt"));

    webhook.execute(ctx, true, payload).await?;
    Ok(())
}

pub async fn global_error_handler(e: FrameworkError<'_, Data, Error>) {
    if let Some(ctx) = e.ctx() {
        if let Err(failure) = webhook_alert(ctx, &e).await {
            error!("Bot could not report errors to discord: {e}, {failure:?}")
        }
    } else {
        error!("Bot could not report errors to discord: {e}")
    }

    match e {
        FrameworkError::Setup { framework, .. } => {
            framework.shard_manager().shutdown_all().await;
        }
        _ => {
            if let Err(e) = builtins::on_error(e).await {
                error!("Error from the error handler: {e:?}");
            }
        }
    }
}
