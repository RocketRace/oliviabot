use std::sync::Arc;

use crate::{Error, Result};
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use regex::Regex;
use rusqlite::{functions::FunctionFlags, vtab::csvtab, Transaction};

pub fn init_db(pool: Pool<SqliteConnectionManager>) -> Result<()> {
    let mut conn = pool.get()?;
    // initialize CSV virtual table module
    csvtab::load_module(&conn)?;
    // implement the REGEXP operator
    conn.create_scalar_function(
        "regexp",
        2,
        FunctionFlags::SQLITE_UTF8 | FunctionFlags::SQLITE_DETERMINISTIC,
        move |ctx| {
            assert_eq!(ctx.len(), 2, "called with unexpected number of arguments");
            let regexp: Arc<Regex> = ctx.get_or_create_aux(0, |vr| -> Result<_, Error> {
                Ok(Regex::new(vr.as_str()?)?)
            })?;

            let is_match = {
                let text = ctx
                    .get_raw(1)
                    .as_str_or_null()
                    .map_err(|e| rusqlite::Error::UserFunctionError(e.into()))?;

                text.map(|text| regexp.is_match(text))
            };

            Ok(is_match)
        },
    )?;
    // run migrations
    let tx = conn.transaction()?;
    init_neofetch(&tx)?;
    tx.commit()?;

    Ok(())
}

fn init_neofetch(tx: &Transaction) -> Result<()> {
    tx.execute_batch(
        "
        CREATE VIRTUAL TABLE IF NOT EXISTS neofetch
        USING csv(
            filename='data/neofetch.csv',
            schema='CREATE TABLE x(
                distro TEXT NOT NULL,
                variant TEXT NOT NULL,
                pattern TEXT NOT NULL,
                logo TEXT NOT NULL,
                mobile_width TEXT NOT NULL
            )'
        )
        ",
    )?;
    Ok(())
}
