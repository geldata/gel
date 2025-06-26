use proc_macro::TokenStream;
use quote::{format_ident, quote};

const OUTPUT_ATTR: &str = "output";
const STUB_ATTR: &str = "stub";

/// Implements [edgeql_parser::grammar::Reduce] for conversion from CST nodes to
/// AST nodes.
///
/// Requires an enum with unit variants only. Each variant name is interpreted
/// as a "production name", which consists of names of parser terms (either
/// Terminals or NonTerminals), delimited by `_`.
///
/// Requires an `#[output(...)]` attribute, which denotes the output type of
/// this parser non-terminal.
///
/// Will generate a `*Args` enum, which contains the reduced AST nodes of child
/// non-terminals. This "node" requires an implementation of `Into<OutputTy>`,
/// or rather `OutputTy` requires `From<Args>`.
///
/// If `#[stub()]` attribute is present, the `From` trait is automatically
/// derived, filled with `todo!()`.
#[proc_macro_derive(Reduce, attributes(output, stub))]
pub fn grammar_non_terminal(input: TokenStream) -> TokenStream {
    let item = syn::parse_macro_input!(input as syn::Item);

    let syn::Item::Enum(enum_item) = item else {
        panic!("Only enums are allowed to be grammar rules")
    };

    let name = &enum_item.ident;
    let node_name = format_ident!("{name}Args");

    let output_ty = get_list_attribute_tokens(&enum_item, OUTPUT_ATTR)
        .unwrap_or_else(|| panic!("missing #[output(...)] attribute"));
    let output_ty: TokenStream = output_ty.clone().into();
    let output_ty: syn::Type = syn::parse_macro_input!(output_ty as syn::Type);

    let is_stub = get_list_attribute(&enum_item, STUB_ATTR).is_some();

    let mut node_variants = proc_macro2::TokenStream::new();
    for variant in &enum_item.variants {
        let variant_name = &variant.ident;

        let mut kids = proc_macro2::TokenStream::new();
        for (_, child_name, is_term) in iter_children(&variant_name.to_string()) {
            if is_term {
                kids.extend(quote! {
                    crate::parser::Terminal,
                });
            } else {
                let non_term_name = format_ident!("{child_name}");
                kids.extend(quote! {
                    <#non_term_name as Reduce>::Output,
                });
            }
        }

        node_variants.extend(quote! {
            #variant_name(#kids),
        });
    }

    let mut match_arms = proc_macro2::TokenStream::new();
    for variant in &enum_item.variants {
        let variant_name = &variant.ident;

        let mut args = proc_macro2::TokenStream::new();
        let mut calls = proc_macro2::TokenStream::new();
        for (index, child_name, is_term) in iter_children(&variant_name.to_string()) {
            let arg_name = format_ident!("arg{index}");

            if is_term {
                calls.extend(quote! {
                    let crate::parser::CSTNode::Terminal(t) = &p.args[#index] else { panic!() };
                    let #arg_name = (*t).clone();
                });
            } else {
                let non_term_name = format_ident!("{child_name}");
                calls.extend(quote! {
                    let #arg_name = <#non_term_name as Reduce>::reduce(&p.args[#index]);
                });
            }

            args.extend(quote! { #arg_name, });
        }

        match_arms.extend(quote! {
            Self::#variant_name => {
                #calls

                let node = #node_name::#variant_name(#args);
                <#node_name as Into<#output_ty>>::into(node)
            }
        });
    }

    let mut stub = proc_macro2::TokenStream::new();
    if is_stub {
        stub.extend(quote! {
            impl From<#node_name> for #output_ty {
                fn from(val: #node_name) -> Self {
                    todo!();
                }
            }
        })
    }

    let output = quote!(
        pub enum #node_name {
            #node_variants
        }

        impl Reduce for #name {
            type Output = #output_ty;

            fn reduce(node: &CSTNode) -> #output_ty {
                let CSTNode::Production(p) = node else { panic!() };
                match Self::from_id(p.id) {
                    #match_arms
                }
            }
        }

        #stub
    );

    TokenStream::from(output)
}

fn get_list_attribute_tokens<'a>(
    enum_item: &'a syn::ItemEnum,
    name: &'static str,
) -> Option<&'a proc_macro2::TokenStream> {
    get_list_attribute(enum_item, name).and_then(|a| match &a.meta {
        syn::Meta::List(ml) => Some(&ml.tokens),
        _ => None,
    })
}

fn get_list_attribute<'a>(
    enum_item: &'a syn::ItemEnum,
    name: &'static str,
) -> Option<&'a syn::Attribute> {
    enum_item.attrs.iter().find_map(|a| match &a.meta {
        syn::Meta::List(ml) => {
            if path_eq(&ml.path, name) {
                Some(a)
            } else {
                None
            }
        }
        _ => None,
    })
}

fn path_eq(path: &syn::Path, name: &str) -> bool {
    path.get_ident().map_or(false, |i| i.to_string() == name)
}

fn iter_children(variant_name: &str) -> impl Iterator<Item = (usize, &str, bool)> {
    variant_name
        .split('_')
        .enumerate()
        .filter(|c| c.1 != "epsilon")
        .map(|(i, t)| {
            let is_terminal = t == t.to_ascii_uppercase();
            (i, t, is_terminal)
        })
}

struct ListParams {
    name: syn::Ident,
    item: syn::Ident,
    output_ty: syn::Type,
    separator: syn::Ident,
    allow_trailing: bool,
}

impl syn::parse::Parse for ListParams {
    fn parse(input: syn::parse::ParseStream) -> syn::Result<Self> {
        input.parse::<syn::Token![enum]>()?;
        let name = input.parse()?;
        input.parse::<syn::Token![,]>()?;

        let item = input.parse()?;
        input.parse::<syn::Token![,]>()?;

        let output_ty = input.parse()?;
        input.parse::<syn::Token![,]>()?;

        let separator = input.parse()?;
        input.parse::<syn::Token![,]>()?;

        let allow_trailing = {
            let lit = input.parse::<syn::LitBool>()?;
            lit.value
        };
        Ok(ListParams {
            name,
            item,
            output_ty,
            separator,
            allow_trailing,
        })
    }
}

#[proc_macro]
pub fn list(input: TokenStream) -> TokenStream {
    let ListParams {
        name,
        item,
        output_ty,
        separator,
        allow_trailing,
    } = syn::parse_macro_input!(input as ListParams);

    let list_node = format_ident!("{name}Args");

    let output = if allow_trailing {
        let inner = format_ident!("{name}Inner");
        let inner_node = format_ident!("{inner}Args");
        let prod_item = &item;
        let prod_inner_sep_elem = format_ident!("{inner}_{separator}_{item}");

        let prod_inner = &inner;
        let prod_inner_sep = format_ident!("{inner}_{separator}");

        quote! {
            #[derive(edgeql_parser_derive::Reduce)]
            #[output(#output_ty)]
            pub enum #name {
                #prod_inner,
                #prod_inner_sep,
            }

            impl From<#list_node> for #output_ty {
                fn from(val: #list_node) -> Self {
                    match val {
                        #list_node::#prod_inner(l) => l,
                        #list_node::#prod_inner_sep(l, _) => l,
                    }
                }
            }

            #[derive(edgeql_parser_derive::Reduce)]
            #[output(#output_ty)]
            pub enum #inner {
                #prod_item,
                #prod_inner_sep_elem,
            }

            impl From<#inner_node> for #output_ty {
                fn from(val: #inner_node) -> Self {
                    match val {
                        #inner_node::#prod_item(e) => {
                            vec![e]
                        },
                        #inner_node::#prod_inner_sep_elem(mut l, _, e) => {
                            l.push(e);
                            l
                        },
                    }
                }
            }
        }
    } else {
        let list_sep_elem = format_ident!("{name}_{separator}_{item}");

        quote! {
            #[derive(edgeql_parser_derive::Reduce)]
            #[output(#output_ty)]
            pub enum #name {
                #item,
                #list_sep_elem,
            }

            impl From<#list_node> for #output_ty {
                fn from(val: #list_node) -> Self {
                    match val {
                        #list_node::#item(e) => {
                            vec![e]
                        },
                        #list_node::#list_sep_elem(mut l, _, e) => {
                            l.push(e);
                            l
                        },
                    }
                }
            }
        }
    };
    TokenStream::from(output)
}
