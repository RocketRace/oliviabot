use std::sync::Arc;

use crate::{Error, Result};
use r2d2::Pool;
use r2d2_sqlite::SqliteConnectionManager;
use regex::{Regex, RegexBuilder};
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
                Ok(RegexBuilder::new(vr.as_str()?)
                    .case_insensitive(true)
                    .build()?)
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
        CREATE VIRTUAL TABLE temp.neofetch
        USING csv(
            filename='data/neofetch.csv',
            header=1,
            schema='CREATE TABLE x(
                distro TEXT NOT NULL,
                suffix TEXT NOT NULL,
                pattern TEXT NOT NULL,
                mobile_width INTEGER NOT NULL,
                color_index INTEGER NOT NULL,
                color_rgb TEXT NOT NULL,
                logo TEXT NOT NULL
            ) STRICT'
        )
        ",
    )?;
    Ok(())
}
