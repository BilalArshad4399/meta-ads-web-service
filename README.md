# Zane - Meta Ads MCP Integration Service

A web service that provides Meta/Facebook Ads ROAS data to Claude AI through the MCP (Model Context Protocol) over SSE (Server-Sent Events).

## Architecture

Zane follows the same pattern as GoMarble and other MCP integrations:
1. Users sign up and connect their Meta Ads accounts
2. Service generates a unique SSE endpoint URL
3. Users add this URL to Claude's integration settings
4. Claude connects via SSE to access Meta Ads data

## Features

- 🔐 User authentication (email/password + Google OAuth ready)
- 📊 Meta Ads account connection and management
- 🤖 MCP protocol implementation over SSE
- 📈 ROAS metrics and performance data
- 🔄 Real-time data streaming to Claude
- 🐳 Docker deployment ready

## Quick Start

### Local Development

1. **Clone and setup:**
```bash
cd meta-ads-web-service
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run the application:**
```bash
python app.py
```

Visit `http://localhost:5000`

### Docker Deployment

```bash
docker-compose up -d
```

The service will be available at `http://localhost`

## How Users Connect to Claude

1. **Sign Up**: Create account at your-domain.com
2. **Connect Meta Ads**: Add Meta Ads accounts with access tokens
3. **Get Integration URL**: Copy unique SSE endpoint from dashboard
4. **Add to Claude**: 
   - Go to claude.ai/settings/integrations
   - Add "Zane" as integration name
   - Paste the integration URL
   - Click Connect

## Available MCP Tools

Once connected, users can ask Claude:

### `get_account_roas`
- "What's my Meta Ads ROAS for last month?"
- Returns overall account metrics

### `get_campaigns_roas`
- "Show me all campaign performance"
- Returns ROAS for all campaigns

### `get_top_performing_ads`
- "What are my top 10 ads by ROAS?"
- Returns best performing ads

### `get_all_accounts_summary`
- "Give me a summary of all my ad accounts"
- Returns combined metrics for all accounts

## API Endpoints

### Authentication
- `POST /auth/signup` - Create new account
- `POST /auth/login` - Login
- `GET /auth/logout` - Logout
- `GET /auth/google` - Google OAuth (placeholder)

### Account Management
- `GET /api/accounts` - List connected Meta Ads accounts
- `POST /api/accounts` - Add new Meta Ads account
- `DELETE /api/accounts/<id>` - Remove account

### MCP Integration
- `GET /mcp-api/sse` - SSE endpoint for Claude
- `POST /mcp-api/rpc` - JSON-RPC endpoint (alternative)
- `GET /api/integration-url` - Get user's integration URL

## Database Schema

### Users
- Email/password authentication
- Google OAuth support
- JWT token generation

### AdAccounts
- Meta Ads account credentials
- Access token storage (encrypted in production)
- Account status tracking

### MCPSessions
- Active Claude connections
- Session management
- Activity tracking

## Security Considerations

1. **Token Security**: 
   - Store Meta access tokens encrypted
   - Use environment variables for secrets
   - Rotate JWT secrets regularly

2. **HTTPS Required**:
   - Always use HTTPS in production
   - SSL configuration included in nginx.conf

3. **Rate Limiting**:
   - Implement rate limiting for API endpoints
   - Monitor for unusual activity

## Production Deployment

### Requirements
- Domain name with SSL certificate
- PostgreSQL database
- Redis for caching (optional)
- Docker or Python hosting

### Environment Variables
```env
SECRET_KEY=strong-random-key
JWT_SECRET=strong-jwt-secret
DATABASE_URL=postgresql://user:pass@host/db
```

### Deployment Steps

1. **Setup server:**
```bash
git clone <your-repo>
cd meta-ads-web-service
```

2. **Configure production:**
```bash
cp .env.example .env
# Edit with production values
```

3. **Deploy with Docker:**
```bash
docker-compose -f docker-compose.yml up -d
```

4. **Setup SSL:**
   - Add SSL certificates to `./ssl/`
   - Update nginx.conf with your domain
   - Uncomment HTTPS configuration

## Getting Meta Ads Access Tokens

Users need to provide their own Meta access tokens:

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create or select an app
3. Navigate to Graph API Explorer
4. Generate User Access Token with permissions:
   - `ads_read`
   - `ads_management`
5. Convert to long-lived token

## Monitoring

- Check `/mcp-api/sse` endpoint health
- Monitor database connections
- Track user sessions and API usage
- Review Meta API rate limits

## Troubleshooting

### SSE Connection Issues
- Ensure nginx proxy_buffering is off
- Check CORS settings
- Verify JWT token validity

### Meta API Errors
- Validate access tokens
- Check account permissions
- Monitor API rate limits

## License

MIT

## Support

For issues or questions about:
- MCP Protocol: Check Claude documentation
- Meta Ads API: Refer to Meta developer docs
- This service: Open an issue on GitHub