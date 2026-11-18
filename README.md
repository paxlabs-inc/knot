# Hyper Package Manager (HPM)

A modern monorepo package manager for any programming language that simplifies dependency management and builds across multiple apps and packages.

## ✨ Features

- **🔗 Smart Package Linking** - Automatic symlinking of local packages
- **☁️ Online Package Support** - Download packages from hpm space (`@package`, `@team/package`)
- **📋 Template System** - Use published packages as templates for new projects
- **⚡ Language Integration** - Per-app configuration with special TypeScript support
- **🔨 Build Management** - Execute build commands across apps or individually
- **▶️ Script Runner** - Run scripts from any config file with `hpm run`
- **📦 Flexible Configuration** - YAML-based configuration with multiple syntax options
- **🌍 Multi-Language Support** - Works with any programming language (Rust, Go, Python, Java, etc.)

## 🚀 Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/paxlabs-inc/knot/main/install.sh | bash
```

### Prerequisites
- **Rust** (1.70+): Install from [rustup.rs](https://rustup.rs/)
- **Git**: For cloning repositories

## 📋 Commands

### Project Management
```bash
hpm init <name> [--description <desc>]    # Initialize a new project
hpm status                                # Show project status
```

### Package & App Management
```bash
hpm init:package <name> [--team <team>] [--template <@package>]  # Create a new package
hpm init:app <name> [--template <@package>]                      # Create a new app

# Examples with templates from HPM Registry:
hpm init:app my-app --template @svelte-starter
hpm init:package my-lib --template @typescript-lib
```

### Linking & Building
```bash
hpm link                                  # Link packages to apps
hpm build                                 # Build apps (context-aware)
hpm run <script>                          # Run scripts from config files
```

### Updates & Maintenance
```bash
hpm update                                # Update to latest version
hpm update --force                        # Force reinstall current version
```

## 🎯 Quick Start

```bash
# 1. Initialize project
hpm init my-monorepo --description "My awesome monorepo"
cd my-monorepo

# 2. Create shared packages (optionally with templates)
cd packages
hpm init:package utils --team myteam
hpm init:package types --team myteam --template @typescript-lib
cd ..

# 3. Create applications (optionally with templates)
cd apps
hpm init:app frontend --description "Web frontend" --template @react-starter
hpm init:app backend --description "API server" --template @fastify-api
cd ..

# 4. Configure dependencies and scripts in hpm.yml
# 5. Link packages and build
hpm link
hpm build

# 6. Run development scripts
hpm run dev    # Run dev script
hpm run test   # Run test script
```

## ⚙️ Configuration

### Project Configuration (`hpm.yml`)

```yaml
name: MyProject
description: My awesome monorepo

# Global project scripts
scripts:
  setup: "npm install && echo 'Setup complete'"
  test-all: "hpm run test --all"
  clean: "rm -rf */dist */build"
  deploy: "hpm build && deploy.sh"

apps:
  frontend:
    tsAlias: "@"
    packages:
      - types
      - utils
      - "@jwt"
  backend:
    tsAlias: "#"
    packages:
      - types
      - "@klysium/logger"
```

### App Configuration (`app.yml`)

```yaml
name: frontend
description: Web frontend app
tsAlias: "~"                    # Optional: Override project tsAlias (TypeScript projects)
build: "npm run build"          # Build command

# App-specific scripts
scripts:
  dev: "npm run dev"
  test: "npm run test"
  lint: "npm run lint"
  serve: "npm run serve"

packages:                       # Optional: Additional packages
  - types
  - utils
  - "@jwt"
```

### Package Configuration (`package.yml`)

```yaml
name: utils
team: myteam      # Optional: Team namespace
version: 1.0.0

# Package scripts
scripts:
  build: "npm run build"
  test: "npm run test"
  docs: "npm run docs"
  benchmark: "npm run benchmark"
```

## 🔨 Build Commands

HPM supports flexible build management with the `hpm build` command:

### Context-Aware Building

- **From project root**: Builds all apps that have build commands configured
- **From app directory**: Builds only the current app

### Configuration

Add build commands to your `app.yml` files:

```yaml
name: frontend
description: Web frontend
build: "npm run build"          # Simple command
# build: "pnpm build --prod"    # Alternative build tools  
# build: "./build.sh"           # Custom scripts
# build: "cargo build --release" # Rust projects
# build: "go build -o bin/app"  # Go projects
```

### Examples

```bash
# Build all apps from project root
cd my-monorepo
hpm build
# Output:
# 🔨 Building all apps for project 'MyProject'...
# 📋 Found 2 app(s) with build commands
# 🔨 Building app 'frontend'...
# 🔨 Building app 'backend'...
# 🎉 All apps built successfully!

# Build single app from app directory
cd apps/frontend
hpm build
# Output:
# 🔨 Building app 'frontend'...
# 📝 Running: npm run build
# ✅ Successfully built app 'frontend'
```

## ▶️ Script Runner

HPM provides a powerful script runner similar to npm scripts, with context-aware execution:

### Context-Aware Script Resolution

Scripts are resolved in priority order:
1. **App directory** (`app.yml`) - Highest priority
2. **Package directory** (`package.yml`) - Medium priority
3. **Project root** (`hpm.yml`) - Lowest priority

### Usage Examples

```bash
# Run scripts from different contexts
cd apps/frontend && hpm run dev     # Runs frontend dev script
cd packages/utils && hpm run test   # Runs utils test script
cd project-root && hpm run setup    # Runs project setup script

# Script not found shows available options
hpm run invalid-script
# Output:
# ❌ Script 'invalid-script' not found
# 💡 Available scripts:
#   📱 App scripts (frontend)
#     • dev - npm run dev
#     • test - npm run test
#     • lint - npm run lint
#   🏗️ Project scripts (MyProject)
#     • setup - npm install && echo 'Setup complete'
#     • clean - rm -rf */dist */build
```

### Script Features

- **Environment variables** - Access to full shell environment
- **Working directory** - Scripts run in their config file's directory
- **Command chaining** - Use `&&` and `||` for complex workflows
- **Cross-platform** - Works on Windows, macOS, and Linux

### Common Script Patterns

```yaml
# Development workflow
scripts:
  dev: "concurrently 'hpm run dev-server' 'hpm run dev-client'"
  dev-server: "npm run start:dev"
  dev-client: "npm run dev"

# Testing pipeline
scripts:
  test: "npm run test"
  test-watch: "npm run test:watch"
  test-e2e: "npm run test:e2e"
  test-all: "hpm run test && hpm run test-e2e"

# Build pipeline
scripts:
  prebuild: "hpm run lint && hpm run test"
  build: "npm run build"
  postbuild: "cp README.md dist/"
```

## 📦 Package Types

### Local Packages
- Located in `packages/` directory
- Referenced by name: `types`, `utils`
- Symlinked to `hpm_packages/` in apps

### Online Packages
- **Public packages**: `@jwt`, `@axios`
- **Team packages**: `@team/package-name`
- Downloaded to `hpm_packages/` in apps

## 🎨 TypeScript Integration (Optional)

HPM works with any programming language, but provides special integration features for TypeScript projects.

### Per-App Aliases
Configure TypeScript path aliases per app:

```yaml
# hpm.yml
apps:
  frontend:
    tsAlias: "@"      # Creates @/* alias
  backend:
    tsAlias: "#"      # Creates #/* alias
```

### Priority Order
1. `app.yml` `tsAlias` (highest priority)
2. `hpm.yml` app-specific `tsAlias`
3. `hpm.yml` global `tsAlias`

### Generated TypeScript Configuration
HPM automatically updates `tsconfig.json` files:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./hpm_packages/*"],
      "src/*": ["./src/*"]
    }
  }
}
```

## 📁 Project Structure

```
my-monorepo/
├── hpm.yml                 # Project configuration
├── packages/               # Local packages
│   ├── types/
│   │   ├── package.yml
│   │   └── src/           # Source files (any language)
│   └── utils/
│       ├── package.yml
│       └── src/           # Source files (any language)
└── apps/                   # Applications
    ├── frontend/
    │   ├── app.yml         # App configuration
    │   ├── tsconfig.json   # Auto-updated (TypeScript projects only)
    │   ├── hpm_packages/  # Linked packages
    │   │   ├── types -> ../../packages/types
    │   │   ├── utils -> ../../packages/utils
    │   │   └── @jwt/       # Downloaded package
    │   └── src/
    └── backend/
        ├── app.yml
        ├── tsconfig.json       # (TypeScript projects only)
        ├── hpm_packages/
        └── src/
```

## 🛠️ Manual Installation

```bash
git clone https://github.com/paxlabs-inc/knot.git
cd hpm/apps/cli
cargo build --release
sudo cp target/release/hpm /usr/local/bin/
```

## 📖 Advanced Usage

### Multiple Package Sources

```yaml
# hpm.yml
apps:
  frontend:
    packages:
      - types              # Local package
      - utils              # Local package
      - "@jwt"            # Public online package
      - "@myteam/logger"  # Team online package
```

### Custom Build Scripts

```yaml
# app.yml
name: frontend
build: "./scripts/build.sh"    # Custom build script
```

```bash
#!/bin/bash
# scripts/build.sh
echo "🔨 Building with custom script..."
npm run lint                    # Or: cargo clippy, go fmt, etc.
npm run test                    # Or: cargo test, go test, etc.  
npm run build:prod              # Or: cargo build --release, go build, etc.
echo "✅ Build complete!"
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Repository**: [https://github.com/paxlabs-inc/knot](https://github.com/paxlabs-inc/knot)
- **Issues**: [https://github.com/paxlabs-inc/knot/issues](https://github.com/paxlabs-inc/knot/issues)
- **Documentation**: [https://github.com/paxlabs-inc/knot](https://github.com/paxlabs-inc/knot)
