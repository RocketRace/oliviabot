use crate::Commands;

mod meta;

pub struct Cog {
    pub commands: Commands,
    pub category: String,
}

impl Cog {
    pub fn new(commands: Commands, category: String) -> Self {
        Self { commands, category }
    }
}

// This is a hacky sort of cog framework around poise's commands.
pub fn commands() -> Commands {
    let cogs = [meta::cog()];

    let mut result = vec![];
    for cog in cogs {
        for command in cog.commands {
            result.push(poise::Command {
                category: Some(cog.category.clone()),
                ..command
            });
        }
    }
    result
}
