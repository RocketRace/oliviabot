use poise::{builtins, FrameworkError};
use tracing::error;

use crate::{state::Data, Error};

pub async fn global_error_handler(e: FrameworkError<'_, Data, Error>) {
    match e {
        FrameworkError::Setup {
            error, framework, ..
        } => {
            error!("Bot encountered error during READY payload: {error}");
            framework.shard_manager().shutdown_all().await;
        }
        _ => {
            if let Err(e) = builtins::on_error(e).await {
                error!("Error from the error handler: {e}");
            }
        }
    }
}
