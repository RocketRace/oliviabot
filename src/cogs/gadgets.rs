use std::time::Duration;

use crate::{Context, Result};

use super::Cog;

pub fn cog() -> Cog {
    Cog::new(vec![], "Gadgets".to_string())
}

#[poise::command(prefix_command, slash_command)]
async fn neofetch(ctx: Context<'_>, distro: Option<String>) -> Result<()> {
    Ok(())
}
