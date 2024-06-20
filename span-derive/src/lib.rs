use proc_macro::TokenStream;
use quote::quote_spanned;
use syn::{parse_macro_input, spanned::Spanned, ItemFn};

/// Injects span information to the `custom_data` field of the `poise::command` output.
#[proc_macro_attribute]
pub fn inject_span(_args: TokenStream, item: TokenStream) -> TokenStream {
    let input = parse_macro_input!(item as ItemFn);

    let fn_name = input.sig.ident.clone();

    let span = input.span();

    let output: proc_macro2::TokenStream = quote_spanned! { span =>
        fn #fn_name() -> ::poise::Command<
            <Context<'static> as poise::_GetGenerics>::U,
            <Context<'static> as poise::_GetGenerics>::E,
        > {
            let file_loc = file!();
            let line_no = line!();

            #input

            let mut command = #fn_name();
            command.custom_data = Box::new(Spanned {
                file: file_loc,
                line: line_no,
                inner: command.custom_data
            }) as Box<dyn ::std::any::Any + ::std::marker::Send + ::std::marker::Sync + 'static>;
            command
        }
    };

    proc_macro::TokenStream::from(output)
}
