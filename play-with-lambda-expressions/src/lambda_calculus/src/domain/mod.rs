//! Pure domain models — no IO, no side effects.

pub mod term;
pub mod parser;
pub mod variables;
pub mod reduction;
pub mod metrics;

pub use term::{Term, fold};
pub use parser::{ParseError, ParseResult, parse, parse_with_info};
pub use variables::{free_vars, bound_vars, binding_vars, is_closed};
pub use reduction::{substitute, alpha_rename, beta_reduce_step, beta_reduce, is_normal_form};
pub use metrics::{
    Meter, Ratio, Size, Depth, AbsDepth, SubtermCount, DeBruijnHeight, BindingDensity,
    term_size, term_depth, abs_depth, subterm_count, de_bruijn_height, binding_density,
};
