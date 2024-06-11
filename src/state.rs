use std::{
    fmt::Debug,
    sync::{Arc, Mutex},
};

use poise::serenity_prelude as serenity;
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use tracing::{info, warn};

use crate::{database, Config, Result};

pub struct Repo {
    pub handle: Arc<Mutex<git2::Repository>>,
    pub url: String,
}

impl Repo {
    pub fn new(handle: Arc<Mutex<git2::Repository>>, url: String) -> Self {
        Self { handle, url }
    }
}

// Shared state
pub struct Data {
    pub repo: Option<Repo>,
    pub db: Pool<SqliteConnectionManager>,
    pub config: Config,
    pub neofetch_updated: serenity::Timestamp,
}

impl Debug for Data {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Data")
            .field("repo", &"<repository handle>" as &dyn Debug)
            .field("db", &self.db)
            .field("config", &self.config)
            .field("neofetch_updated", &self.neofetch_updated)
            .finish()
    }
}

impl Data {
    pub async fn from_config(config: &Config) -> Result<Self> {
        info!("Connecting to the database");
        let manager = r2d2_sqlite::SqliteConnectionManager::file(&config.database_url);
        let pool = Pool::new(manager)?;

        info!("Initializing database modules and running migrations");
        database::init_db(pool.clone())?;

        let updated_unix = std::fs::read_to_string("data/neofetch_updated")?
            .trim()
            .parse::<i64>()?;
        let neofetch_updated = serenity::Timestamp::from_unix_timestamp(updated_unix)?;

        let mut data = Data {
            repo: None,
            config: config.clone(),
            db: pool,
            neofetch_updated,
        };

        info!("Discovering local git repository");
        match git2::Repository::discover(".") {
            Ok(repo) => {
                let url = repo
                    .find_remote("origin")?
                    .url()
                    .ok_or("Repository remote URL is invalid UTF-8")?
                    .trim_end_matches(".git")
                    .to_string();

                data.repo = Some(Repo::new(Arc::new(Mutex::new(repo)), url));
            }
            Err(e) => {
                warn!("Could not open a git repository; some features will be unavailable. Detailed error:\n{e}");
            }
        }

        info!("Initialized state");
        Ok(data)
    }
}
