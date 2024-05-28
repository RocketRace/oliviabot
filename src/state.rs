use std::sync::{Arc, Mutex};

use sqlx::SqlitePool;
use tracing::{info, warn};

use crate::{PublicConfig, Result};

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
    pub db: SqlitePool,
}

impl Data {
    pub async fn from_config(config: &PublicConfig) -> Result<Self> {
        let mut data = Data {
            repo: None,
            db: SqlitePool::connect(&config.database_url).await?,
        };

        info!("Running migrations");
        sqlx::migrate!().run(&data.db).await?;

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
