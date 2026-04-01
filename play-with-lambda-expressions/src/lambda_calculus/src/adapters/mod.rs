//! Concrete implementations wired at the composition root.

pub mod random_gen;
pub mod memory_names;
pub mod readline_ui;
pub mod script_ui;

pub use random_gen::RandomTermGenerator;
pub use memory_names::InMemoryNameRegistry;
pub use readline_ui::ReadlineUI;
pub use script_ui::ScriptUI;
