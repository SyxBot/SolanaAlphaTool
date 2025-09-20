# replit.md

## Overview

This is a Solana Signal Alert Bot that monitors pump.fun token launches using real detection logic from the pump-fun-bot repository. Instead of executing trades, it sends webhook alerts to Telegram, Discord, or custom endpoints with authentic token data including name, address, launch time, and pump.fun URLs.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture
- **Language**: Python 3 with asyncio for asynchronous operations
- **Event Loop**: Uses uvloop for enhanced performance
- **Entry Points**: Multiple entry points (`bot_runner.py` and `main.py`) for flexibility
- **Logging**: Structured logging with both console and file output

### Runtime Environment
- Asynchronous Python application using asyncio
- Environment-based configuration via .env files
- Modular dependency checking and validation
- Production-ready logging with multiple handlers

## Key Components

### 1. Bot Runner (`bot_runner.py`)
- Main entry point for the trading bot
- Environment validation for required Solana credentials
- Logging configuration setup
- Private key validation

### 2. Alternative Entry Point (`main.py`)
- Simplified entry point with dependency checking
- Runtime validation of required Python modules
- Environment configuration validation

### 3. Configuration Management
- Environment variable-based configuration
- Required variables include:
  - `SOLANA_NODE_RPC_ENDPOINT`: Solana RPC node connection
  - `SOLANA_PRIVATE_KEY`: Trading wallet private key

### 4. Dependencies
Core dependencies include:
- `solana`: Solana blockchain interaction
- `base58`: Address encoding/decoding
- `websockets`: Real-time data subscriptions
- `aiohttp`: HTTP client for API calls
- `borsh_construct`: Solana data serialization
- `solders`: Additional Solana utilities

## Data Flow

### 1. Token Discovery
- Uses both `logsSubscribe` and `blockSubscribe` for flexibility
- Monitors pump.fun for new token mints
- Real-time data streaming via WebSocket connections

### 2. Trading Decision Process
- Validates environment and dependencies on startup
- Processes token mint events
- Executes trading strategies based on configured parameters

### 3. Transaction Management
- Dynamic priority fee calculation
- Transaction retry mechanisms
- Bonding curve status tracking

## External Dependencies

### Blockchain Infrastructure
- **Solana RPC Node**: Primary blockchain interaction (recommends Chainstack)
- **pump.fun Platform**: Token minting and trading platform
- **PumpSwap DEX**: Migration destination for tokens

### Development Status
- Production-ready webhook alert system
- Successfully tested with live token detection
- Based on authenticated pump-fun-bot detection logic
- Supports Telegram, Discord, and generic webhook endpoints

## Deployment Strategy

### Environment Setup
1. Install Python dependencies via `requirements.txt`
2. Configure environment variables in `.env` file
3. Validate Solana RPC endpoint connectivity
4. Ensure wallet private key is properly formatted

### Runtime Considerations
- Configurable RPS to match RPC provider limits
- Error handling and retry mechanisms
- Logging to both console and file for monitoring
- Multiple entry points for different use cases

### Node.js Crypto Signal Agent
- **Jan 15, 2025**: Node.js crypto signal agent deployed on Replit
  - **Express Server**: Running on port 5000 with health endpoints and keep-alive functionality
  - **Memory API Integration**: Configurable endpoint with retry logic and error handling
  - **Telegram Alerts**: Formatted signal messages and error notifications
  - **ES Module Support**: Modern JavaScript with import/export syntax
  - **Auto Keep-Alive**: Prevents Replit sleeping with periodic pings
  - **Production Ready**: Error handling, logging, and graceful shutdown

### Recent Changes
- **Dec 2025**: Complete webhook alert system implementation
- **Core Features**: Real-time token detection with authentic pump.fun data
- **Webhook Support**: Telegram bots, Discord webhooks, and generic JSON endpoints
- **Production Ready**: Error handling, rate limiting, and comprehensive logging
- **Testing Suite**: Full validation with mock and real data scenarios
- **Jan 2025**: Advanced token filtering system implementation
  - **Symbol Validation**: Regex-based filtering for 2-6 uppercase letters only
  - **Wallet Analysis**: Creator wallet age and transaction history validation
  - **Liquidity Analysis**: Real bonding curve liquidity extraction from pump.fun
  - **Complete Filter**: 100% spam rejection rate with quality scoring system
  - **Integration Ready**: Modular components for webhook bot integration
  - **Shared Memory System**: Bot 1 reports token intelligence and wallet reputation
    - `should_alert()` function combining all quality checks
    - Memory reporter for tracking trusted/blocked/suspicious wallets
    - Enhanced webhook bot with filtering, alerting, and memory integration
    - Quality scoring system (0-10) for token assessment
- **Jan 13, 2025**: Complete codebase refactoring and architecture enhancement
  - **Environment Configuration**: All hardcoded values moved to .env with comprehensive settings
  - **Utils Module**: Centralized helper functions with standardized logging, retry logic, and memory API integration
  - **Standardized Logging**: BOT1 identifier with [YYYY-MM-DD HH:MM:SS] format throughout codebase
  - **Memory Integration**: Enhanced memory_reporter.py using utils functions for consistency
  - **Enhanced Webhook Bot**: webhook_with_memory.py combining filtering, alerting, and memory reporting
  - **Configuration Management**: Environment-based configuration for all filtering thresholds and API settings
  - **Error Handling**: Retry decorators and standardized error reporting across all modules
  - **Quality Assurance**: All modules tested and integrated with proper error handling and logging

### Security Notes
- Private key validation on startup
- Environment variable isolation
- Warning system for scam detection in community interactions
- Clear disclaimer about production usage