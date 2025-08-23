# Deployment Guide for GoMarble MCP Server

## Current Status
The MCP server has been updated with a simplified implementation that follows the MCP protocol specification for Claude integration.

## Changes Made
1. Created simplified MCP server (`app/mcp_simple.py`) with:
   - Proper JSON-RPC 2.0 protocol handling
   - Initialize, tools/list, and tools/call methods
   - Demo Meta Ads data for testing
   - No authentication required (for initial testing)

2. Server responds correctly to:
   - GET / - Returns server capabilities
   - POST / - Handles MCP protocol messages
   - HEAD / - Discovery endpoint

## Deployment Steps

### 1. Push to GitHub
Since you need authentication, you have two options:

#### Option A: Use GitHub Personal Access Token
```bash
# Create a personal access token on GitHub:
# Settings > Developer settings > Personal access tokens > Generate new token

# Update git remote to use token
git remote set-url origin https://YOUR_TOKEN@github.com/BilalArshad4399/meta-ads-web-service.git

# Push changes
git push origin main
```

#### Option B: Use GitHub Desktop or Web Interface
- Use GitHub Desktop app to push changes
- Or manually upload files via GitHub web interface

### 2. Verify Koyeb Deployment
- Check your Koyeb dashboard for auto-deployment
- If not configured, manually trigger deployment
- Wait for deployment to complete (usually 2-3 minutes)

### 3. Test Deployed Server
Run the test script to verify:
```bash
python3 test_mcp.py
```

Expected results:
- GET / should return 200 with server info
- HEAD / should return 200
- POST / with initialize should work

### 4. Add to Claude

Once deployed, add to Claude:
1. Go to claude.ai/settings/integrations
2. Click "Add Integration"
3. Enter:
   - Name: GoMarble Meta Ads
   - URL: https://deep-audy-wotbix-9060bbad.koyeb.app
4. Click "Add" then "Connect"

### 5. Test in Claude
Once connected, you should be able to use commands like:
- "Get my Meta Ads overview"
- "Show campaign performance"
- "Get ad insights"

## Troubleshooting

### If Claude can't connect:
1. Check server logs on Koyeb
2. Verify endpoints are responding:
   ```bash
   curl https://deep-audy-wotbix-9060bbad.koyeb.app/
   ```
3. Check CORS headers are present
4. Ensure server returns proper JSON-RPC responses

### If tools don't appear:
1. Verify tools/list method returns tools
2. Check initialize method returns capabilities
3. Ensure proper JSON-RPC format in responses

## Next Steps
Once basic connection works, you can:
1. Add real Meta Ads API integration
2. Implement OAuth authentication
3. Add more sophisticated tools
4. Connect actual user accounts

## Environment Variables
Make sure these are set on Koyeb:
- `BASE_URL=https://deep-audy-wotbix-9060bbad.koyeb.app`
- `JWT_SECRET=<secure-random-string>`
- `SECRET_KEY=<secure-random-string>`