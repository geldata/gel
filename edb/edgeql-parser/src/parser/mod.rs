mod cst;
mod custom_errors;
mod spec;

pub use cst::{CSTNode, Production, Terminal};
pub use spec::{Action, Reduce, Spec, SpecSerializable};

use append_only_vec::AppendOnlyVec;

use crate::keywords::{self, Keyword};
use crate::position::Span;
use crate::tokenizer::{Error, Kind, Value};

pub struct Context<'s> {
    spec: &'s Spec,
    arena: bumpalo::Bump,
    terminal_arena: AppendOnlyVec<Terminal>,
}

impl<'s> Context<'s> {
    pub fn new(spec: &'s Spec) -> Self {
        Context {
            spec,
            arena: bumpalo::Bump::new(),
            terminal_arena: AppendOnlyVec::new(),
        }
    }
}

/// This is a const just so we remember to update it everywhere
/// when changing.
const UNEXPECTED: &str = "Unexpected";

pub fn parse<'a>(input: &'a [Terminal], ctx: &'a Context) -> (Option<CSTNode<'a>>, Vec<Error>) {
    let stack_top = ctx.arena.alloc(StackNode {
        parent: None,
        state: 0,
        value: CSTNode::Empty,
    });
    let initial_track = Parser {
        stack_top,
        error_cost: 0,
        node_count: 0,
        can_recover: true,
        errors: Vec::new(),
        has_custom_error: false,
    };

    // Append EIO token.
    // We have a weird setup that requires two EOI tokens:
    // - one is consumed by the grammar generator and does not contribute to
    //   span of the nodes.
    // - second is consumed by explicit EOF tokens in EdgeQLGrammar NonTerm.
    //   Since these are children of productions, they do contribute to the
    //   spans of the top-level nodes.
    // First EOI is produced by tokenizer (with correct offset) and second one
    // is injected here.
    let end = input.last().map(|t| t.span.end).unwrap_or_default();
    let eoi = ctx.alloc_terminal(Terminal {
        kind: Kind::EOI,
        span: Span { start: end, end },
        text: "".to_string(),
        value: None,
        is_placeholder: false,
    });
    let input = input.iter().chain([eoi]);

    let mut parsers = vec![initial_track];
    let mut prev_span: Option<Span> = None;
    let mut new_parsers = Vec::with_capacity(parsers.len() + 5);

    for token in input {
        // println!("token {:?}", token);

        while let Some(mut parser) = parsers.pop() {
            let res = parser.act(ctx, token);

            if res.is_ok() {
                // base case: ok
                parser.node_successful();
                new_parsers.push(parser);
            } else {
                // error: try to recover

                let gap_span = {
                    let prev_end = prev_span.map(|p| p.end).unwrap_or(token.span.start);

                    Span {
                        start: prev_end,
                        end: token.span.start,
                    }
                };

                // option 1: inject a token
                if parser.error_cost <= ERROR_COST_INJECT_MAX && !parser.has_custom_error {
                    let possible_actions = &ctx.spec.actions[parser.stack_top.state];
                    for token_kind in possible_actions.keys() {
                        if parser.can_act(ctx, token_kind).is_none() {
                            continue;
                        }

                        let mut inject = parser.clone();

                        let injection =
                            new_token_for_injection(*token_kind, &prev_span, token.span, ctx);

                        let cost = injection_cost(token_kind);
                        let error = Error::new(format!("Missing {injection}")).with_span(gap_span);
                        inject.push_error(error, cost);

                        if inject.error_cost <= ERROR_COST_INJECT_MAX
                            && inject.act(ctx, injection).is_ok()
                        {
                            // println!("   --> [inject {injection}]");

                            // insert into parsers, to retry the original token
                            parsers.push(inject);
                        }
                    }
                }

                // option 2: check for a custom error and skip token
                //   Due to performance reasons, this is done only on first
                //   error, not during all the steps of recovery.
                if parser.error_cost == 0 {
                    if let Some(error) = parser.custom_error(ctx, token) {
                        parser
                            .push_error(error.default_span_to(token.span), ERROR_COST_CUSTOM_ERROR);
                        parser.has_custom_error = true;

                        // println!("   --> [custom error]");
                        new_parsers.push(parser);
                        continue;
                    }
                } else if parser.has_custom_error {
                    // when there is a custom error, just skip the tokens until
                    // the parser recovers
                    // println!("   --> [skip because of custom error]");
                    new_parsers.push(parser);
                    continue;
                }

                // option 3: skip the token
                let mut skip = parser;
                let error = Error::new(format!("{UNEXPECTED} {token}")).with_span(token.span);
                skip.push_error(error, ERROR_COST_SKIP);
                if token.kind == Kind::EOI || token.kind == Kind::Semicolon {
                    // extra penalty
                    skip.error_cost += ERROR_COST_INJECT_MAX;
                    skip.can_recover = false;
                }

                // insert into new_parsers, so the token is skipped
                // println!("   --> [skip] {}", skip.error_cost);
                new_parsers.push(skip);
            }
        }

        // has any parser recovered?
        if new_parsers.len() > 1 {
            new_parsers.sort_by_key(Parser::adjusted_cost);

            if new_parsers[0].has_custom_error {
                // if we have a custom error, just keep that

                new_parsers.drain(1..);
            } else if new_parsers[0].has_recovered() {
                // recover parsers whose "adjusted error cost" reached 0 and discard the rest

                new_parsers.retain(|p| p.has_recovered());
                for p in &mut new_parsers {
                    p.error_cost = 0;
                }
            } else if new_parsers[0].error_cost > ERROR_COST_INJECT_MAX {
                // prune: pick only 1 best parsers that has cost > ERROR_COST_INJECT_MAX

                new_parsers.drain(1..);
            } else if new_parsers.len() > PARSER_COUNT_MAX {
                // prune: pick only X best parsers

                new_parsers.drain(PARSER_COUNT_MAX..);
            }
        }

        assert!(parsers.is_empty());
        std::mem::swap(&mut parsers, &mut new_parsers);
        prev_span = Some(token.span);

        // for (index, parser) in parsers.iter().enumerate() {
        //     print!(
        //         "p{index} {:06} {:5}:",
        //         parser.error_cost, parser.can_recover
        //     );
        //     for e in &parser.errors {
        //         print!(" {}", e.message);
        //     }
        //     println!("");
        // }
        // println!("");
    }

    // there will always be a parser left,
    // since we always allow a token to be skipped
    let parser = parsers
        .into_iter()
        .min_by(|a, b| {
            Ord::cmp(&a.error_cost, &b.error_cost).then_with(|| {
                Ord::cmp(
                    &starts_with_unexpected_error(a),
                    &starts_with_unexpected_error(b),
                )
                .reverse()
            })
        })
        .unwrap();

    let node = parser.finish(ctx);
    let errors = custom_errors::post_process(parser.errors);
    (node, errors)
}

/// Parses tokens and then inspects the state of the parser to suggest possible
/// next keywords and a boolean indicating if next token can be an identifier.
/// This is done by looking at available actions in current state.
/// An important detail is that not all of these actions are valid.
/// They might trigger a chain of reductions that ends in a state that
/// does not accept the suggested token.
pub fn suggest_next_keyword<'a>(input: &'a [Terminal], ctx: &'a Context) -> (Vec<Keyword>, bool) {
    // init
    let stack_top = ctx.arena.alloc(StackNode {
        parent: None,
        state: 0,
        value: CSTNode::Empty,
    });
    let mut parser = Parser {
        stack_top,
        error_cost: 0,
        node_count: 0,
        can_recover: true,
        errors: Vec::new(),
        has_custom_error: false,
    };

    // parse tokens
    for token in input.iter() {
        if matches!(token.kind, Kind::EOI) {
            break;
        }

        let res = parser.act(ctx, token);

        if res.is_err() {
            return (vec![], false);
        }
    }

    // extract possible next actions
    let actions = &ctx.spec.actions[parser.stack_top.state];

    let can_be_ident =
        actions.contains_key(&Kind::Ident) && parser.can_act(ctx, &Kind::Ident).is_some();

    let keywords = actions
        .keys()
        // suggest only keywords
        .filter_map(|kind| {
            if let Kind::Keyword(keyword) = kind {
                Some(*keyword)
            } else {
                None
            }
        })
        // never suggest dunder or bools, they should be suggested semantically
        .filter(|k| !k.is_dunder() && !k.is_bool())
        // if next token can be ident, hide all unreserved keywords
        .filter(|k| !(can_be_ident && k.is_unreserved()))
        // filter only valid actions
        .filter(|k| parser.can_act(ctx, &Kind::Keyword(*k)).is_some())
        .collect();

    (keywords, can_be_ident)
}

fn starts_with_unexpected_error(a: &Parser) -> bool {
    a.errors
        .first()
        .is_none_or(|x| x.message.starts_with(UNEXPECTED))
}

impl Context<'_> {
    fn alloc_terminal(&self, t: Terminal) -> &'_ Terminal {
        let idx = self.terminal_arena.push(t);
        &self.terminal_arena[idx]
    }

    fn alloc_slice_and_push(&self, slice: &Option<&[usize]>, element: usize) -> &[usize] {
        let curr_len = slice.map_or(0, |x| x.len());
        let mut new = Vec::with_capacity(curr_len + 1);
        if let Some(inlined_ids) = slice {
            new.extend(*inlined_ids);
        }
        new.push(element);
        self.arena.alloc_slice_clone(new.as_slice())
    }
}

fn new_token_for_injection<'a>(
    kind: Kind,
    prev_span: &Option<Span>,
    next_span: Span,
    ctx: &'a Context,
) -> &'a Terminal {
    let (text, value) = match kind {
        Kind::Keyword(Keyword(kw)) => (kind.text(), Some(Value::String(kw.to_string()))),
        Kind::Ident => {
            let ident = "ident_placeholder";
            (Some(ident), Some(Value::String(ident.into())))
        }
        _ => (kind.text(), None),
    };

    ctx.alloc_terminal(Terminal {
        kind,
        text: text.unwrap_or_default().to_string(),
        value,
        span: Span {
            start: prev_span.map_or(0, |x| x.end),
            end: next_span.start,
        },
        is_placeholder: true,
    })
}

struct StackNode<'p> {
    parent: Option<&'p StackNode<'p>>,

    state: usize,
    value: CSTNode<'p>,
}

#[derive(Clone)]
struct Parser<'s> {
    stack_top: &'s StackNode<'s>,

    /// sum of cost of every error recovery action
    error_cost: u16,

    /// number of nodes pushed to stack since last error
    node_count: u16,

    /// prevent parser from recovering, for cases when EOF was skipped
    can_recover: bool,

    errors: Vec<Error>,

    /// A flag that is used to make the parser prefer custom errors over other
    /// recovery paths
    has_custom_error: bool,
}

impl<'s> Parser<'s> {
    fn act(&mut self, ctx: &'s Context, token: &'s Terminal) -> Result<(), ()> {
        // self.print_stack();
        // println!("INPUT: {}", token.text);

        loop {
            // find next action
            let Some(action) = ctx.spec.actions[self.stack_top.state].get(&token.kind) else {
                return Err(());
            };

            match action {
                Action::Shift(next) => {
                    // println!("   --> [shift {next}]");

                    // push on stack
                    self.push_on_stack(ctx, *next, CSTNode::Terminal(token));
                    return Ok(());
                }
                Action::Reduce(reduce) => {
                    self.reduce(ctx, reduce);
                }
            }
        }
    }

    fn reduce(&mut self, ctx: &'s Context, reduce: &'s Reduce) {
        let args = ctx.arena.alloc_slice_fill_with(reduce.cnt, |_| {
            let v = self.stack_top.value;
            self.stack_top = self.stack_top.parent.unwrap();
            v
        });
        args.reverse();

        let value = CSTNode::Production(Production {
            id: reduce.production_id,
            span: get_span_of_nodes(args),
            args,
            inlined_ids: None,
        });

        let nstate = self.stack_top.state;

        let next = *ctx.spec.goto[nstate].get(&reduce.non_term).unwrap();

        // inline (if there is an inlining rule)
        let mut value = value;
        if let CSTNode::Production(production) = value {
            if let Some(inline_position) = ctx.spec.inlines.get(&production.id) {
                let inlined_id = production.id;
                // inline rule found
                let args = production.args;

                value = args[*inline_position as usize];

                // save inlined id
                if let CSTNode::Production(new_prod) = &mut value {
                    new_prod.inlined_ids =
                        Some(ctx.alloc_slice_and_push(&new_prod.inlined_ids, inlined_id));
                }
            } else {
                // place back
                value = CSTNode::Production(production);
            }
        }

        self.push_on_stack(ctx, next, value);

        // println!(
        //     "   --> [reduce {} ::= ({} popped) at {}/{}]",
        //     production, cnt, state, nstate
        // );
        // self.print_stack();
    }

    pub fn push_on_stack(&mut self, ctx: &'s Context, state: usize, value: CSTNode<'s>) {
        let node = StackNode {
            parent: Some(self.stack_top),
            state,
            value,
        };
        self.stack_top = ctx.arena.alloc(node);
    }

    pub fn finish(&self, _ctx: &'s Context) -> Option<CSTNode<'s>> {
        if !self.can_recover || self.has_custom_error {
            return None;
        }

        // pop the EOI from the top of the stack
        assert!(
            matches!(
                &self.stack_top.value,
                CSTNode::Terminal(Terminal {
                    kind: Kind::EOI,
                    ..
                })
            ),
            "expected EOI CST node, got {:?}",
            self.stack_top.value
        );

        let final_node = self.stack_top.parent.unwrap();

        // self.print_stack(_ctx);
        // println!("   --> accept");

        let first = final_node.parent.unwrap();
        assert!(
            matches!(&first.value, CSTNode::Empty),
            "expected empty CST node, found {:?}",
            first.value
        );

        Some(final_node.value)
    }

    /// Lightweight version of act that checks if a token *could* be applied.
    /// Returns next state.
    fn can_act(&self, ctx: &'s Context, token: &Kind) -> Option<usize> {
        let mut state = self.stack_top.state;

        let mut node = &self.stack_top;

        // count of "ghost" stack nodes, which should have been pushed to the stack,
        // but haven't because we don't actually need them there, only need to know
        // how many of them there are
        let mut ghosts = 0;

        loop {
            // find next action
            let action = ctx.spec.actions[state].get(token)?;

            match action {
                Action::Shift(next) => {
                    return Some(*next);
                }
                Action::Reduce(reduce) => {
                    // simulate reduce stack pops
                    // (cancel out any ghost nodes if there is any)
                    let cancel_out = usize::min(ghosts, reduce.cnt);
                    ghosts -= cancel_out;
                    for _ in 0..(reduce.cnt - cancel_out) {
                        node = node.parent.as_ref().unwrap();
                    }

                    // get state of current stack top
                    // Stack top is node.state, unless we have ghosts. In that case, the
                    // state of node we would have pushed is stored in `state`.
                    let stack_state = if ghosts > 0 { state } else { node.state };

                    state = *ctx.spec.goto[stack_state].get(&reduce.non_term)?;

                    ghosts += 1;
                }
            }
        }
    }

    #[cfg(never)]
    fn print_stack(&self, ctx: &'s Context) {
        let prefix = "STACK: ";

        let mut stack = Vec::new();
        let mut node = Some(self.stack_top);
        while let Some(n) = node {
            stack.push(n);
            node = n.parent.clone();
        }
        stack.reverse();

        let names = stack
            .iter()
            .map(|s| match s.value {
                CSTNode::Empty => format!("Empty"),
                CSTNode::Terminal(term) => format!("{term}"),
                CSTNode::Production(prod) => {
                    let prod_name = &ctx.spec.production_names[prod.id];
                    format!("{}.{}", prod_name.0, prod_name.1)
                }
            })
            .collect::<Vec<_>>();

        let mut states = format!("{:5}", ' ');
        for (index, node) in stack.iter().enumerate() {
            let name_width = names[index].chars().count();
            states += &format!("  {:<width$}", node.state, width = name_width);
        }

        println!("{}{}", prefix, names.join("  "));
        println!("{}", states);
    }

    fn push_error(&mut self, error: Error, cost: u16) {
        let mut suppress = false;
        if error.message.starts_with(UNEXPECTED) {
            if let Some(last) = self.errors.last() {
                if last.message.starts_with(UNEXPECTED) {
                    // don't repeat "Unexpected" errors

                    // This is especially useful when we encounter an
                    // unrecoverable error which will make all tokens until EOF
                    // as "Unexpected".
                    suppress = true;
                }
            }
        }
        if !suppress {
            self.errors.push(error);
        }

        self.error_cost += cost;
        self.node_count = 0;
    }

    fn node_successful(&mut self) {
        self.node_count += 1;
    }

    /// Error cost, subtracted by a function of successfully parsed nodes.
    fn adjusted_cost(&self) -> u16 {
        let x = self.node_count.saturating_sub(3);
        self.error_cost.saturating_sub(x.saturating_mul(x))
    }

    fn has_recovered(&self) -> bool {
        self.can_recover && self.adjusted_cost() == 0
    }

    fn get_from_top(&self, steps: usize) -> Option<&StackNode<'s>> {
        self.stack_top.step_up(steps)
    }
}

impl<'a> StackNode<'a> {
    fn step_up(&self, steps: usize) -> Option<&StackNode<'a>> {
        let mut node = Some(self);
        for _ in 0..steps {
            match node {
                None => return None,
                Some(n) => node = n.parent,
            }
        }
        node
    }
}

/// Returns the span of syntactically ordered nodes. Panic on empty nodes.
fn get_span_of_nodes(nodes: &[CSTNode]) -> Option<Span> {
    let start = nodes.iter().find_map(|x| match x {
        CSTNode::Terminal(t) => Some(t.span.start),
        CSTNode::Production(p) => Some(p.span?.start),
        CSTNode::Empty => panic!(),
    })?;
    let end = nodes.iter().rev().find_map(|x| match x {
        CSTNode::Terminal(t) => Some(t.span.end),
        CSTNode::Production(p) => Some(p.span?.end),
        CSTNode::Empty => panic!(),
    })?;
    Some(Span { start, end })
}

const PARSER_COUNT_MAX: usize = 10;

const ERROR_COST_INJECT_MAX: u16 = 15;
const ERROR_COST_SKIP: u16 = 3;
const ERROR_COST_CUSTOM_ERROR: u16 = 3;

fn injection_cost(kind: &Kind) -> u16 {
    use Kind::*;

    match kind {
        Ident => 10,
        Substitution => 8,

        // Manual keyword tweaks to encourage some error messages and discourage others.
        Keyword(keywords::Keyword(
            "delete" | "update" | "migration" | "role" | "global" | "administer" | "future"
            | "database" | "serializable" | "REPEATABLE" | "NOT", //  | "if" | "group",
        )) => 100,
        Keyword(keywords::Keyword("insert" | "module" | "extension" | "branch")) => 20,
        Keyword(keywords::Keyword("select" | "property" | "type")) => 10,
        Keyword(_) => 15,

        Dot => 5,
        OpenBrace | OpenBracket => 5,
        OpenParen => 4,

        CloseBrace | CloseBracket | CloseParen => 1,

        Namespace => 10,
        Comma | Colon | Semicolon => 2,
        Eq => 5,

        At => 6,
        IntConst => 8,

        Assign | Arrow => 5,

        _ => 100, // forbidden
    }
}
