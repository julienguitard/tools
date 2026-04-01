//! CLI entry point for the lambda calculus REPL.

use std::path::PathBuf;
use clap::Parser;

#[derive(Parser)]
#[command(about = "Interactive untyped lambda calculus REPL.")]
struct Cli {
    /// Maximum beta-reduction steps before stopping.
    #[arg(long, default_value_t = 100)]
    max_steps: usize,

    /// Default AST depth for :random.
    #[arg(long, default_value_t = 3)]
    random_depth: usize,

    /// Run a script file instead of the interactive REPL.
    #[arg(long)]
    script: Option<PathBuf>,
}

fn main() {
    let cli = Cli::parse();

    if let Some(script_path) = cli.script {
        let content = match std::fs::read_to_string(&script_path) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Error: {}: {}", script_path.display(), e);
                std::process::exit(1);
            }
        };
        let lines: Vec<String> = content.lines().map(String::from).collect();
        let mut repl = lambda_calculus::service::make_script_repl(
            lines,
            cli.max_steps,
            cli.random_depth,
        );
        repl.run();
    } else {
        let mut repl = lambda_calculus::service::make_repl(
            cli.max_steps,
            cli.random_depth,
        );
        repl.run();
    }
}
