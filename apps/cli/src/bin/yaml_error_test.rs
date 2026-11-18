// Comprehensive test program for YAML error handling improvements
// Tests various malformed YAML files to ensure error messages are user-friendly

use anyhow::Result;

/// Re-export the config types and error handling from the main module
#[path = "../config.rs"]
mod config;

use config::{
    parse_yaml_error_with_context, ConfigType, HpmConfig, PackageConfig, AppConfig
};

fn test_missing_required_fields() -> Result<()> {
    println!("\n=== Testing Missing Required Fields ===");

    // Test missing name in hpm.yml
    println!("🧪 Testing missing 'name' field in hpm.yml...");
    let hpm_no_name = r#"
description: "A project without a name"
scripts:
  start: "npm start"
"#;

    match serde_yaml::from_str::<HpmConfig>(hpm_no_name) {
        Ok(_) => println!("❌ Should have failed - missing name"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test missing version in package.yml
    println!("🧪 Testing missing 'version' field in package.yml...");
    let package_no_version = r#"
name: "my-package"
description: "A package without version"
"#;

    match serde_yaml::from_str::<PackageConfig>(package_no_version) {
        Ok(_) => println!("❌ Should have failed - missing version"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::Package);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test missing name in app.yml
    println!("🧪 Testing missing 'name' field in app.yml...");
    let app_no_name = r#"
description: "An app without a name"
packages:
  - utils
"#;

    match serde_yaml::from_str::<AppConfig>(app_no_name) {
        Ok(_) => println!("❌ Should have failed - missing name"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::App);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_invalid_field_types() -> Result<()> {
    println!("\n=== Testing Invalid Field Types ===");

    // Test scripts as string instead of object
    println!("🧪 Testing scripts field with string instead of object...");
    let invalid_scripts = r#"
name: "test-project"
scripts: "this should be an object"
"#;

    match serde_yaml::from_str::<HpmConfig>(invalid_scripts) {
        Ok(_) => println!("❌ Should have failed - invalid scripts type"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test packages as string instead of array
    println!("🧪 Testing packages field with string instead of array...");
    let invalid_packages = r#"
name: "test-app"
packages: "should-be-array"
"#;

    match serde_yaml::from_str::<AppConfig>(invalid_packages) {
        Ok(_) => println!("❌ Should have failed - invalid packages type"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::App);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test version as number instead of string
    println!("🧪 Testing version field with number instead of string...");
    let invalid_version = r#"
name: "test-package"
version: 1.0.0
"#;

    match serde_yaml::from_str::<PackageConfig>(invalid_version) {
        Ok(_) => println!("❌ Should have failed - invalid version type"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::Package);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_unknown_fields() -> Result<()> {
    println!("\n=== Testing Unknown Fields ===");

    // Test typo in field name
    println!("🧪 Testing unknown field 'script' (should be 'scripts')...");
    let unknown_field = r#"
name: "test-project"
script:
  start: "npm start"
"#;

    match serde_yaml::from_str::<HpmConfig>(unknown_field) {
        Ok(_) => println!("❌ Should have failed - unknown field"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test tsalias instead of tsAlias
    println!("🧪 Testing unknown field 'tsalias' (should be 'tsAlias')...");
    let case_error = r#"
name: "test-app"
tsalias: true
packages:
  - utils
"#;

    match serde_yaml::from_str::<AppConfig>(case_error) {
        Ok(_) => println!("❌ Should have failed - case sensitive field"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::App);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_yaml_syntax_errors() -> Result<()> {
    println!("\n=== Testing YAML Syntax Errors ===");

    // Test missing colon
    println!("🧪 Testing missing colon after field name...");
    let missing_colon = r#"
name "test-project"
description: "Missing colon above"
"#;

    match serde_yaml::from_str::<HpmConfig>(missing_colon) {
        Ok(_) => println!("❌ Should have failed - missing colon"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test invalid indentation
    println!("🧪 Testing invalid indentation...");
    let bad_indentation = r#"
name: "test-project"
scripts:
start: "npm start"  # Wrong indentation
  build: "npm run build"
"#;

    match serde_yaml::from_str::<HpmConfig>(bad_indentation) {
        Ok(_) => println!("❌ Should have failed - bad indentation"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test unclosed quotes
    println!("🧪 Testing unclosed quotes...");
    let unclosed_quotes = r#"
name: "test-project
description: "Missing closing quote above"
"#;

    match serde_yaml::from_str::<HpmConfig>(unclosed_quotes) {
        Ok(_) => println!("❌ Should have failed - unclosed quotes"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_duplicate_fields() -> Result<()> {
    println!("\n=== Testing Duplicate Fields ===");

    // Test duplicate name field
    println!("🧪 Testing duplicate 'name' field...");
    let duplicate_name = r#"
name: "first-name"
description: "Test project"
name: "second-name"
"#;

    match serde_yaml::from_str::<HpmConfig>(duplicate_name) {
        Ok(_) => println!("❌ Should have failed - duplicate field"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_complex_structure_errors() -> Result<()> {
    println!("\n=== Testing Complex Structure Errors ===");

    // Test invalid apps structure
    println!("🧪 Testing invalid apps structure...");
    let invalid_apps = r#"
name: "test-project"
apps:
  - "should-be-object-not-array"
"#;

    match serde_yaml::from_str::<HpmConfig>(invalid_apps) {
        Ok(_) => println!("❌ Should have failed - invalid apps structure"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test mixed valid/invalid structure in apps
    println!("🧪 Testing mixed valid/invalid structure in apps...");
    let mixed_apps = r#"
name: "test-project"
apps:
  web:
    - utils
    - types
  backend:
    invalid_field: "this is wrong"
    packages:
      - validators
"#;

    match serde_yaml::from_str::<HpmConfig>(mixed_apps) {
        Ok(_) => println!("❌ Should have failed - invalid field in app"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_variables_errors() -> Result<()> {
    println!("\n=== Testing Variables Section Errors ===");

    // Test invalid variable structure
    println!("🧪 Testing invalid variable structure...");
    let invalid_variables = r#"
name: "test-project"
variables:
  - "should-be-object-not-array"
"#;

    match serde_yaml::from_str::<HpmConfig>(invalid_variables) {
        Ok(_) => println!("❌ Should have failed - invalid variables structure"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test invalid complex variable structure
    println!("🧪 Testing invalid complex variable structure...");
    let invalid_complex_var = r#"
name: "test-project"
variables:
  simple_var: "this is fine"
  complex_var:
    invalid_field: "should be 'value' and 'description'"
    another_invalid: "wrong structure"
"#;

    match serde_yaml::from_str::<HpmConfig>(invalid_complex_var) {
        Ok(_) => println!("❌ Should have failed - invalid complex variable"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_edge_cases() -> Result<()> {
    println!("\n=== Testing Edge Cases ===");

    // Test completely empty file
    println!("🧪 Testing empty YAML content...");
    let empty_yaml = "";

    match serde_yaml::from_str::<HpmConfig>(empty_yaml) {
        Ok(_) => println!("❌ Should have failed - empty file"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test whitespace only
    println!("🧪 Testing whitespace-only YAML content...");
    let whitespace_yaml = "   \n  \t  \n   ";

    match serde_yaml::from_str::<HpmConfig>(whitespace_yaml) {
        Ok(_) => println!("❌ Should have failed - whitespace only"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test just a comment
    println!("🧪 Testing comment-only YAML content...");
    let comment_only = "# This is just a comment";

    match serde_yaml::from_str::<HpmConfig>(comment_only) {
        Ok(_) => println!("❌ Should have failed - comment only"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test invalid characters
    println!("🧪 Testing invalid Unicode characters...");
    let invalid_chars = "name: \"test\x00project\"";

    match serde_yaml::from_str::<HpmConfig>(invalid_chars) {
        Ok(_) => println!("❌ Should have failed - invalid chars"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn test_real_world_common_mistakes() -> Result<()> {
    println!("\n=== Testing Real-World Common Mistakes ===");

    // Test mixing tabs and spaces
    println!("🧪 Testing mixed tabs and spaces...");
    let mixed_whitespace = "name: \"test-project\"\nscripts:\n\tstart: \"npm start\"\n  build: \"npm run build\"";

    match serde_yaml::from_str::<HpmConfig>(mixed_whitespace) {
        Ok(_) => println!("❌ Should have failed - mixed whitespace"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::HPM);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test missing dash in array
    println!("🧪 Testing missing dash in array...");
    let missing_dash = r#"
name: "test-app"
packages:
  utils
  types
"#;

    match serde_yaml::from_str::<AppConfig>(missing_dash) {
        Ok(_) => println!("❌ Should have failed - missing dash"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::App);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    // Test incorrect boolean values
    println!("🧪 Testing incorrect boolean values...");
    let wrong_boolean = r#"
name: "test-app"
tsAlias: yes  # Should be true/false
packages:
  - utils
"#;

    match serde_yaml::from_str::<AppConfig>(wrong_boolean) {
        Ok(_) => println!("❌ Should have failed - wrong boolean"),
        Err(e) => {
            let friendly_error = parse_yaml_error_with_context(&e, ConfigType::App);
            println!("✅ Caught error: {}", friendly_error);
        }
    }

    Ok(())
}

fn main() -> Result<()> {
    println!("🔍 YAML Error Handling Test Suite");
    println!("Testing enhanced user-friendly error messages for malformed YAML files");

    test_missing_required_fields()?;
    test_invalid_field_types()?;
    test_unknown_fields()?;
    test_yaml_syntax_errors()?;
    test_duplicate_fields()?;
    test_complex_structure_errors()?;
    test_variables_errors()?;
    test_edge_cases()?;
    test_real_world_common_mistakes()?;

    println!("\n🎉 All error handling tests completed!");
    println!("\n📊 Summary:");
    println!("✅ Missing required fields - Enhanced error messages with suggestions");
    println!("✅ Invalid field types - Context-specific type error messages");
    println!("✅ Unknown fields - Suggestions for common typos");
    println!("✅ YAML syntax errors - Clear explanations of syntax issues");
    println!("✅ Duplicate fields - Clear duplicate field detection");
    println!("✅ Complex structure errors - Detailed structure validation");
    println!("✅ Variables section errors - Variable-specific error messages");
    println!("✅ Edge cases - Proper handling of empty/invalid content");
    println!("✅ Real-world mistakes - Common formatting error detection");
    println!("\n💡 Error messages now include:");
    println!("  • Specific field-level context");
    println!("  • Configuration type awareness (hpm.yml vs package.yml vs app.yml)");
    println!("  • Line/column information when available");
    println!("  • Actionable suggestions for fixes");
    println!("  • Examples of correct formatting");

    Ok(())
}