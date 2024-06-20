use poise::{
    builtins,
    serenity_prelude::{
        self as serenity, CreateAllowedMentions, CreateAttachment, CreateEmbed, ExecuteWebhook,
        Mentionable, Timestamp, Webhook,
    },
    FrameworkError,
};
use tap::Pipe;
use tracing::error;

use crate::{config::CONFIG, state::Data, Context};

async fn get_webhook(ctx: &Context<'_>) -> anyhow::Result<Webhook> {
    let url = &CONFIG.secrets.webhook_url;
    Ok(ctx.http().get_webhook_from_url(url).await?)
}

pub async fn global_error_handler(e: FrameworkError<'_, Data, anyhow::Error>) {
    let report = ErrorReport::from_error(&e).await;
    let payload = report.into_payload();

    if let Some(ctx) = e.ctx() {
        match get_webhook(&ctx).await {
            Ok(webhook) => {
                if let Err(failure) = webhook.execute(ctx.http(), true, payload).await {
                    error!("Failed to report error with webhook ({failure}, original error: {e:?}")
                }
            }
            Err(failure) => error!(
                "Could not initialize a reporting webhook ({failure}), original error: {e:?}"
            ),
        }
    } else {
        error!("Error (occurred outside of proper context): {e:?}")
    }

    if let FrameworkError::Setup { framework, .. } = &e {
        framework.shard_manager().shutdown_all().await;
    } else if let Err(e) = builtins::on_error(e).await {
        error!("Error from the error handler: {e:?}");
    }
}

#[derive(Default, Clone, Copy)]
enum Severity {
    #[default]
    Hmm,
    Bad,
    VeryBad,
}

impl Severity {
    fn color(&self) -> serenity::Color {
        match self {
            Severity::Hmm => serenity::Color::from_rgb(32, 224, 224),
            Severity::Bad => serenity::Color::from_rgb(255, 128, 32),
            Severity::VeryBad => serenity::Color::from_rgb(255, 32, 64),
        }
    }
}

#[derive(Default)]
struct ErrorError {
    short_message: String,
    detailed_message: Option<String>,
    backtrace: Option<String>,
}

#[derive(Default)]
struct ErrorContext {
    content: Option<String>,
    author: Option<serenity::User>,
    channel: Option<serenity::GuildChannel>,
    guild: Option<serenity::Guild>,
    command: Option<String>,
    jump_url: Option<String>,
}

#[derive(Default)]
struct ErrorReport {
    severity: Severity,
    error: ErrorError,
    context: ErrorContext,
    timestamp: serenity::Timestamp,
}

impl ErrorError {
    fn from_error(error: &anyhow::Error) -> Self {
        ErrorError {
            short_message: format!("{error}"),
            detailed_message: Some(format!("{error:?}")),
            backtrace: Some(error.backtrace().to_string()),
        }
    }
}

impl ErrorContext {
    async fn from_context(ctx: &Context<'_>) -> Self {
        ErrorContext {
            content: Some(ctx.invocation_string()),
            author: Some(ctx.author().clone()),
            channel: ctx.guild_channel().await,
            guild: ctx.guild().as_deref().cloned(),
            command: Some(ctx.invoked_command_name().to_string()),
            jump_url: if let Context::Prefix(ctx) = ctx {
                Some(ctx.msg.link())
            } else {
                None
            },
        }
    }
}

impl ErrorReport {
    fn into_payload(self) -> ExecuteWebhook {
        let embed = CreateEmbed::new()
            .color(self.severity.color())
            .timestamp(self.timestamp)
            .title(if let Some(command) = self.context.command {
                format!("Error in {command}: {}", self.error.short_message)
            } else {
                format!("Error: {}", self.error.short_message)
            })
            .pipe(|embed| {
                if let Some(detailed_message) = self.error.detailed_message {
                    embed.description(detailed_message)
                } else {
                    embed
                }
            })
            .pipe(|embed| {
                if let Some(content) = self.context.content {
                    embed.field(
                        "Invocation",
                        content.chars().take(1024).collect::<String>(),
                        true,
                    )
                } else {
                    embed
                }
            })
            .pipe(|embed| {
                if let Some(author) = self.context.author {
                    embed.field(
                        "Author",
                        format!("{} (ID: {})", author.tag(), author.id),
                        true,
                    )
                } else {
                    embed
                }
            })
            .pipe(|embed| {
                if let Some(channel) = self.context.channel {
                    if let Some(guild) = self.context.guild {
                        embed.field(
                            "In",
                            format!("{} / {}", guild.name, channel.mention()),
                            true,
                        )
                    } else {
                        embed.field("In", channel.mention().to_string(), true)
                    }
                } else {
                    embed
                }
            })
            .pipe(|embed| {
                if let Some(jump_url) = self.context.jump_url {
                    embed.field("Jump", format!("[Jump to message]({})", jump_url), true)
                } else {
                    embed
                }
            });

        ExecuteWebhook::new()
            .embed(embed)
            .pipe(|payload| {
                if let Some(backtrace) = self.error.backtrace {
                    payload.add_file(CreateAttachment::bytes(backtrace, "backtrace.txt"))
                } else {
                    payload
                }
            })
            .pipe(|payload| {
                if let Severity::VeryBad = self.severity {
                    payload
                        .content("@everyone")
                        .allowed_mentions(CreateAllowedMentions::new().everyone(true))
                } else {
                    payload
                }
            })
    }
    async fn from_error(e: &FrameworkError<'_, Data, anyhow::Error>) -> Self {
        match e {
            FrameworkError::Command { error, ctx, .. } => ErrorReport {
                severity: Severity::Bad,
                error: ErrorError::from_error(error),
                context: ErrorContext::from_context(ctx).await,
                timestamp: ctx.created_at(),
            },
            FrameworkError::CommandPanic { payload, ctx, .. } => ErrorReport {
                severity: Severity::Bad,
                error: ErrorError {
                    short_message: "Command panicked".into(),
                    detailed_message: None,
                    backtrace: payload.clone(),
                },
                context: ErrorContext::from_context(ctx).await,
                timestamp: ctx.created_at(),
            },
            FrameworkError::Setup { error, .. } => ErrorReport {
                severity: Severity::VeryBad,
                error: ErrorError::from_error(error),
                timestamp: Timestamp::now(),
                ..Default::default()
            },
            _ => ErrorReport {
                timestamp: serenity::Timestamp::now(),
                ..Default::default()
            },
        }
    }
}
