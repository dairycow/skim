# IBKR Web API Documentation

## Overview

The IBKR Web API is a RESTful API that provides programmatic access to Interactive Brokers' trading platform and account management features.

**API Version:** 2.17.0  
**Contact:** api@interactivebrokers.com  
**Documentation:** https://ibkrcampus.com/ibkr-api-page/ibkr-api-home/

## Servers

| Environment | URL |
|-------------|-----|
| Production | https://api.ibkr.com |
| Sandbox | https://qa.interactivebrokers.com |

## API Categories

### Account Management
- **Accounts** - Account creation, management, and status
- **Banking** - Bank instructions, transfers, and cash management
- **Reports** - Statements, tax forms, and financial reports
- **Utilities** - Enumerations, forms, and request status

### Authorization
- **SSO Sessions** - Single sign-on session management
- **Token** - Access token creation and management

### Trading
- **Accounts** - Trading account information and balances
- **Alerts** - Market alerts and notifications
- **Contracts** - Contract search and information
- **FA Allocation Management** - Financial advisor allocation groups
- **FYIs and Notifications** - System notifications and bulletins
- **Market Data** - Historical and live market data
- **OAuth 1.0a** - Third-party authentication
- **Orders** - Order placement, modification, and management
- **Portfolio** - Portfolio positions and analysis
- **Portfolio Analyst** - Performance analysis and reporting
- **Scanner** - Market scanning tools
- **Session** - Trading session management
- **Watchlists** - Custom watchlist management
- **Websocket** - Real-time data streaming

### Utilities
- **Echo** - Request validation and testing

## Key Endpoints by Category

### Account Management - Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Create Account |
| PATCH | `/` | Update Account |
| GET | `/` | Get Account Information |
| GET | `/` | Get Status Of Accounts |
| GET | `/` | Get Login Messages |
| POST | `/` | Submit General Agreements And Disclosures |

### Account Management - Banking

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Manage Bank Instructions |
| POST | `/` | Transfer Positions Externally (ACATS, ATON, FOP, DWAC) |
| POST | `/` | Transfer Cash Externally |
| POST | `/` | View Cash Balances |
| POST | `/` | Get Transaction History |
| POST | `/` | Transfer Positions Internally |
| POST | `/` | Transfer Cash Internally |

### Account Management - Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Generate Statements |
| GET | `/` | Fetch Available Report Dates |
| POST | `/` | Fetch Tax Forms |
| GET | `/` | Fetch List Of Available Tax Reports |

### Authorization - Token

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Create Access Token |

### Authorization - SSO Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Create SSO Browser Session |
| POST | `/` | Create New SSO Session On Behalf Of End-user |

### Trading - Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | General Account Summary |
| GET | `/` | Summary Of Available Funds |
| GET | `/` | Summary Of Account Balances |
| GET | `/` | Summary Of Account Margin |
| GET | `/` | Account Profit And Loss |
| GET | `/` | Receive Brokerage Accounts For Current User |
| POST | `/` | Switch Account |

### Trading - Contracts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Returns List Of Contracts Based On Symbol |
| POST | `/` | Returns List Of Contracts Based On Symbol |
| GET | `/` | Contract Information By Contract ID |
| GET | `/` | Currency Exchange Rate |
| GET | `/` | Future Security Definition By Symbol |
| GET | `/` | Stock Security Definition By Symbol |
| GET | `/` | Trading Schedule By Symbol |

### Trading - Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Request Historical Data (OHLC Bars) |
| GET | `/` | Live Market Data Snapshot |
| POST | `/` | Close Backend Stream For Instrument |
| GET | `/` | Close All Open Backend Data Streams |
| GET | `/` | Request Regulatory Snapshot |

### Trading - Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Submit New Order(s) |
| GET | `/` | Retrieve Status Of Single Order |
| GET | `/` | Retrieve Open Orders |
| POST | `/` | Modify Existing Order |
| DELETE | `/` | Cancel Existing Order |
| GET | `/` | Retrieve List Of Trades |
| POST | `/` | Preview Order Effects |
| POST | `/` | Respond To Server Prompt |

### Trading - Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get All Positions In An Account |
| GET | `/` | Get Positions In Accounts For Given Instrument |
| GET | `/` | Get Ledger Data For Given Account |
| GET | `/` | Get Account's Attributes |
| GET | `/` | Portfolio Account Summary |
| POST | `/` | Discard Cached Portfolio Positions |

### Trading - Scanner

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | HMDS Scanner Parameters |
| POST | `/` | HMDS Market Scanner |
| GET | `/` | Iserver Scanner Parameters |
| POST | `/` | Iserver Market Scanner |

### Trading - Session

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Initialise Brokerage Session |
| POST | `/` | Brokerage Session Auth Status |
| GET | `/` | Re-authenticate Brokerage Session |
| POST | `/` | Logout Of Current Session |
| GET | `/` | Validate SSO |
| POST | `/` | Server Ping |

### Trading - OAuth 1.0a

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/` | Request Access Token |
| POST | `/` | Generate Live Session Token |
| POST | `/` | Request Temporary Token |

### Trading - Websocket

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Open Websocket |

## Authentication

The IBKR Web API uses OAuth 1.0a for authentication. The typical flow involves:

1. **Request Temporary Token** - Begin the OAuth workflow
2. **User Authorization** - User grants access to the application
3. **Request Access Token** - Exchange temporary token for access token
4. **Generate Live Session Token** - Create session for API access

## Rate Limits

- Consult the official IBKR API documentation for specific rate limits
- Different endpoints may have different rate limiting policies
- Implement proper backoff and retry logic in your application

## Error Handling

The API returns standard HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

## SDKs and Libraries

- Official Python SDK available
- Third-party libraries for various programming languages
- REST API can be used with any HTTP client library

## Support

- **Email:** api@interactivebrokers.com
- **Documentation:** https://ibkrcampus.com/ibkr-api-page/ibkr-api-home/
- **Community:** IBKR API forums and community resources

---

*This documentation is based on IBKR Web API version 2.17.0. For the most up-to-date information, please refer to the official IBKR API documentation.*