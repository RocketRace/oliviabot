use crate::Commands;

mod meta;

// Having a list of exported commands helps prevent accidentally forgetting to add commands to the bot.
pub fn commands() -> Commands {
    let mut result = vec![];
    result.append(&mut meta::commands());
    result
}
