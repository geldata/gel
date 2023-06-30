use std::collections::HashMap;

use serde::Deserialize;
use serde::Serialize;

use crate::helpers::quote_name;
use crate::position::Span;
use crate::tokenizer::Error;
use crate::tokenizer::Kind;
use crate::tokenizer::Value;

pub fn parse(spec: &Spec, input: Vec<Terminal>) -> (Option<CSTNode>, Vec<Error>) {
    let arena = bumpalo::Bump::new();

    let stack_top = arena.alloc(StackNode {
        parent: None,
        state: 0,
        value: CSTNode::Empty,
    });
    let initial_track = Parser {
        stack_top,
        error_cost: 0,
        errors: Vec::new(),
    };

    let ctx = Context::new(spec, &arena);

    // append EIO
    let end = input.last().map(|t| t.span.end).unwrap_or_default();
    let eio = Terminal {
        kind: Kind::EOI,
        span: Span { start: end, end },
        text: "".to_string(),
        value: None,
    };
    let input = [input, vec![eio]].concat();

    let mut parsers = vec![initial_track];

    for token in input {
        let mut new_parsers = Vec::with_capacity(parsers.len() + 5);

        while let Some(mut parser) = parsers.pop() {
            let res = parser.act(&ctx, &token);

            if res.is_ok() {
                // base case: ok
                new_parsers.push(parser);
            } else {
                // error: try to recover

                // option 1: inject a token
                let possible_actions = &ctx.spec.actions[parser.stack_top.state];
                for token_kind in possible_actions.keys() {
                    let mut inject = parser.clone();

                    let injection = Terminal {
                        kind: token_kind.clone(),
                        text: "".to_string(),
                        value: None,
                        span: Span::default(),
                    };

                    let cost = error_cost(token_kind);
                    let error = Error::new(format!("Missing {injection}")).with_span(token.span);
                    if inject.try_push_error(error, cost) {
                        // println!("   --> [inject {injection}]");

                        if inject.act(&ctx, &injection).is_ok() {
                            // insert into parsers, to retry the original token
                            parsers.push(inject);
                        }
                    }
                }

                // option 2: skip the token
                if token.kind != Kind::EOF {
                    let mut skip = parser;
                    let error = Error::new(format!("Unexpected {token}")).with_span(token.span);
                    if skip.try_push_error(error, ERROR_COST_SKIP) {
                        // println!("   --> [skip]");

                        // insert into new_parsers, so the token is skipped
                        new_parsers.push(skip);
                    }
                }
            }
        }

        parsers = new_parsers;
    }

    // TODO: handle error here
    let mut parser = parsers.into_iter().min_by_key(|p| p.error_cost).unwrap();
    parser.finish();

    let node = Some(parser.stack_top.value.clone());
    (node, parser.errors)
}

pub struct Spec {
    pub actions: Vec<HashMap<Kind, Action>>,
    pub goto: Vec<HashMap<String, usize>>,
    pub start: String,
    pub inlines: HashMap<usize, u8>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Action {
    Shift(usize),
    Reduce(Reduce),
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Reduce {
    /// Index of the production in the associated production array
    pub production_id: usize,

    pub non_term: String,

    /// Number of arguments
    pub cnt: usize,
}

#[derive(Clone)]
pub enum CSTNode {
    Empty,
    Terminal(Terminal),
    Production(Production),
}

#[derive(Clone, Debug)]
pub struct Terminal {
    pub kind: Kind,
    pub text: String,
    pub value: Option<Value>,
    pub span: Span,
}

#[derive(Clone)]
pub struct Production {
    pub id: usize,
    pub args: Vec<CSTNode>,
}

struct StackNode<'p> {
    parent: Option<&'p StackNode<'p>>,

    state: usize,
    value: CSTNode,
}

struct Context<'s> {
    spec: &'s Spec,
    arena: &'s bumpalo::Bump,
}

#[derive(Clone)]
struct Parser<'s> {
    stack_top: &'s StackNode<'s>,

    error_cost: u16,
    errors: Vec<Error>,
}

impl<'s> Context<'s> {
    fn new(spec: &'s Spec, arena: &'s bumpalo::Bump) -> Self {
        Context { spec, arena }
    }
}

impl<'s> Parser<'s> {
    fn act(&mut self, ctx: &'s Context, token: &Terminal) -> Result<(), ()> {
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
                    self.stack_top = ctx.arena.alloc(StackNode {
                        parent: Some(self.stack_top),
                        state: *next,
                        value: CSTNode::Terminal(token.clone()),
                    });
                    return Ok(());
                }
                Action::Reduce(reduce) => {
                    self.reduce(ctx, reduce);
                }
            }
        }
    }

    fn reduce(&mut self, ctx: &'s Context, reduce: &'s Reduce) {
        let mut args = Vec::new();
        for _ in 0..reduce.cnt {
            args.push(self.stack_top.value.clone());
            self.stack_top = self.stack_top.parent.unwrap();
        }
        args.reverse();

        let value = CSTNode::Production(Production {
            id: reduce.production_id,
            args,
        });

        let nstate = self.stack_top.state;

        let next = *ctx.spec.goto[nstate].get(&reduce.non_term).unwrap();

        // inline (if there is an inlining rule)
        let mut value = value;
        if let CSTNode::Production(production) = value {
            if let Some(inline_position) = ctx.spec.inlines.get(&production.id) {
                let mut args = production.args;
                value = args.swap_remove(*inline_position as usize);
            } else {
                value = CSTNode::Production(production);
            }
        }

        // push on stack
        self.stack_top = ctx.arena.alloc(StackNode {
            parent: Some(self.stack_top),
            state: next,
            value,
        });

        // println!(
        //     "   --> [reduce {} ::= ({} popped) at {}/{}]",
        //     production, cnt, state, nstate
        // );
        // self.print_stack();
    }

    pub fn finish(&mut self) {
        debug_assert!(matches!(
            &self.stack_top.value,
            CSTNode::Terminal(Terminal {
                kind: Kind::EOI,
                ..
            })
        ));
        self.stack_top = self.stack_top.parent.unwrap();

        // self.print_stack();
        // println!("   --> accept");

        #[cfg(debug_assertions)]
        {
            let first = self.stack_top.parent.unwrap();
            assert!(matches!(
                &first.value,
                CSTNode::Terminal(Terminal {
                    kind: Kind::Epsilon,
                    ..
                })
            ));
        }
    }

    #[cfg(never)]
    fn print_stack(&self) {
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
            .map(|s| format!("{:?}", s.value))
            .collect::<Vec<_>>();

        let mut states = format!("{:6}", ' ');
        for (index, node) in stack.iter().enumerate() {
            let name_width = names[index].chars().count();
            states += &format!(" {:<width$}", node.state, width = name_width);
        }

        println!("{}{}", prefix, names.join(" "));
        println!("{}", states);
    }

    fn try_push_error(&mut self, error: Error, cost: u16) -> bool {
        self.errors.push(error);
        self.error_cost += cost;
        return self.error_cost <= ERROR_COST_MAX;
    }
}

const ERROR_COST_MAX: u16 = 15;
const ERROR_COST_SKIP: u16 = 2;

fn error_cost(kind: &Kind) -> u16 {
    use Kind::*;

    match kind {
        Ident => 10,
        Substitution => 8,
        Keyword(_) => 10,

        Dot | BackwardLink => 5,
        OpenBrace | OpenBracket | OpenParen => 5,

        CloseBrace | CloseBracket | CloseParen => 1,

        Namespace => 10,
        Colon | Semicolon | Comma | Eq => 5,

        At => 5,
        IntConst => 8,

        Assign | AddAssign | SubAssign | Arrow => 10,

        _ => 100, // forbidden
    }
}

impl std::fmt::Display for Terminal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.kind {
            Kind::EOF => f.write_str("end of line"),
            Kind::Ident => f.write_str(&quote_name(&self.text)),
            _ => write!(f, "token: {}", self.text),
        }
    }
}

impl Default for CSTNode {
    fn default() -> Self {
        CSTNode::Empty
    }
}
