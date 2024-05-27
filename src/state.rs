use std::sync::{Arc, Mutex};

use tracing::warn;

use crate::Result;

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
#[derive(Default)]
pub struct Data {
    pub repo: Option<Repo>,
}

impl Data {
    pub fn new() -> Result<Self> {
        let mut data = Data::default();
        match git2::Repository::discover(".") {
            Ok(repo) => {
                let url = repo
                    .find_remote("origin")?
                    .url()
                    .ok_or("Repository remote URL is invalid UTF-8")?
                    .to_string();

                data.repo = Some(Repo::new(Arc::new(Mutex::new(repo)), url));
            }
            Err(e) => {
                warn!("Could not open a git repository; some features will be unavailable. Detailed error:\n{e}");
            }
        }

        Ok(data)
    }
}
