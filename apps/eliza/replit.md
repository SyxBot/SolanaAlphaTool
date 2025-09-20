# Crypto Market Assistant

## Overview

This is a full-stack crypto market monitoring and analysis application built as an AI-powered trading assistant. The application tracks cryptocurrency data from multiple sources, analyzes market trends, identifies trading opportunities, and provides real-time alerts and insights. It features a React frontend with a dark theme, an Express.js backend with WebSocket support, and PostgreSQL database integration via Drizzle ORM.

The system is designed to monitor Solana tokens specifically, aggregating data from various free APIs including DEXScreener, Birdeye, CoinGecko, and others. It provides volume ranking, trend detection, smart money tracking, and alert generation capabilities to help users make informed trading decisions.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter for lightweight client-side routing
- **State Management**: TanStack Query (React Query) for server state management
- **Styling**: Tailwind CSS with shadcn/ui component library using "new-york" style
- **Real-time Updates**: WebSocket client for live data streaming
- **Build Tool**: Vite with custom configuration for monorepo structure

### Backend Architecture
- **Runtime**: Node.js with Express.js framework
- **Language**: TypeScript with ES modules
- **API Pattern**: REST endpoints with WebSocket server for real-time updates
- **Services**: Modular service architecture including data aggregation, alert management, and Telegram integration
- **Error Handling**: Centralized error middleware with structured error responses

### Data Storage Solutions
- **Database**: PostgreSQL via Neon serverless connection
- **ORM**: Drizzle ORM with code-first schema approach
- **Schema**: Comprehensive data model including tokens, alerts, data sources, system metrics, users, and Telegram configuration
- **Migrations**: Drizzle Kit for database schema management

### Authentication and Authorization
- **Current State**: Basic user schema defined but authentication not fully implemented
- **Future Plans**: Session-based authentication with PostgreSQL session storage using connect-pg-simple

### External Service Integrations
- **Crypto Data Sources**: Multiple API integrations for comprehensive market data
- **Notification System**: Telegram bot integration for alert delivery (ACTIVE - bot connected and operational)
- **Data Validation**: Zod schemas for runtime type checking and validation

### Current System Status
- **Data Aggregation**: Active - polling top 25 tokens every 60s, tokens 26-50 every 120s
- **WebSocket Updates**: Active - real-time dashboard updates every 30s
- **Alert System**: Active - monitoring volume spikes, price movements, and whale activity
- **Telegram Bot**: Connected and operational with automated summary capabilities
- **API Health**: All data sources (DEXScreener, Birdeye, CoinGecko) functioning properly

## External Dependencies

### Crypto Data APIs
- **DEXScreener**: Primary source for token pair data, volume, and liquidity information
- **Birdeye**: Trending Solana tokens and additional market metrics
- **CoinGecko**: General cryptocurrency market data and trending lists
- **CoinMarketCap**: Alternative market data source
- **Jupiter Price API**: Price normalization and aggregation
- **Solana RPC/Helius**: On-chain data and transaction monitoring
- **DefiLlama**: DeFi protocol metrics and broader market analysis

### Third-party Services
- **Neon Database**: Serverless PostgreSQL hosting
- **Telegram Bot API**: Alert delivery and notification system
- **Replit Infrastructure**: Development and deployment platform with specialized plugins

### Development Tools
- **Radix UI**: Accessible component primitives for the UI library
- **Tailwind CSS**: Utility-first CSS framework
- **TypeScript**: Type safety across the entire stack
- **ESBuild**: Fast JavaScript bundler for production builds
- **Vite**: Development server and build tool with HMR support