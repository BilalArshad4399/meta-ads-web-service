#!/usr/bin/env node
/**
 * STDIO to HTTP Bridge for Claude Desktop
 * Connects Claude Desktop to remote MCP server
 */

const readline = require('readline');
const https = require('https');

const SERVER_URL = 'https://deep-audy-wotbix-9060bbad.koyeb.app';

// Setup STDIO
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Buffer for incomplete messages
let buffer = '';

// Log to stderr so it doesn't interfere with JSON-RPC
function log(message) {
  process.stderr.write(`[Bridge] ${message}\n`);
}

// Make HTTP request to remote server
function makeRequest(data) {
  return new Promise((resolve, reject) => {
    const url = new URL(SERVER_URL);
    const postData = typeof data === 'string' ? data : JSON.stringify(data);
    
    const options = {
      hostname: url.hostname,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      
      res.on('data', (chunk) => {
        responseData += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 204) {
          // No content response for notifications
          resolve(null);
        } else if (res.statusCode === 200) {
          try {
            const parsed = JSON.parse(responseData);
            resolve(parsed);
          } catch (e) {
            log(`Failed to parse response: ${responseData.substring(0, 100)}`);
            // Send error response
            resolve({
              jsonrpc: '2.0',
              error: {
                code: -32700,
                message: 'Parse error from server'
              },
              id: null
            });
          }
        } else {
          log(`Server returned status ${res.statusCode}: ${responseData.substring(0, 100)}`);
          resolve({
            jsonrpc: '2.0',
            error: {
              code: -32603,
              message: `Server error: ${res.statusCode}`
            },
            id: null
          });
        }
      });
    });

    req.on('error', (e) => {
      log(`Request error: ${e.message}`);
      resolve({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: `Network error: ${e.message}`
        },
        id: null
      });
    });

    req.write(postData);
    req.end();
  });
}

// Process complete JSON-RPC messages
async function processMessage(messageStr) {
  try {
    const message = JSON.parse(messageStr);
    log(`Received: ${message.method || 'response'} (id: ${message.id})`);
    
    // Forward to HTTP server
    const response = await makeRequest(message);
    
    // Send response back to Claude if not a notification
    if (response !== null) {
      // Ensure we have proper id
      if (message.id !== undefined && response.id === undefined) {
        response.id = message.id;
      }
      
      const responseStr = JSON.stringify(response);
      console.log(responseStr); // Use console.log for STDIO output
      log(`Sent response for id: ${response.id}`);
    }
  } catch (error) {
    log(`Error processing message: ${error.message}`);
    // Try to parse for id
    let messageId = null;
    try {
      const msg = JSON.parse(messageStr);
      messageId = msg.id;
    } catch (e) {
      // Ignore
    }
    
    // Send error response
    const errorResponse = {
      jsonrpc: '2.0',
      error: {
        code: -32603,
        message: error.message
      },
      id: messageId
    };
    console.log(JSON.stringify(errorResponse));
  }
}

// Process incoming messages from Claude Desktop
rl.on('line', async (line) => {
  // Add line to buffer
  buffer += line;
  
  // Try to parse as complete JSON message
  try {
    // Check if we have a complete JSON object
    JSON.parse(buffer);
    
    // If we get here, we have a complete message
    await processMessage(buffer);
    buffer = ''; // Clear buffer
  } catch (e) {
    // Not a complete JSON yet, might be multiline
    // Check if it looks like we should have a complete message
    if (buffer.includes('"jsonrpc"') && buffer.includes('}')) {
      // Try to extract complete JSON objects
      const messages = buffer.split('\n').filter(l => l.trim());
      for (const msg of messages) {
        if (msg.trim()) {
          try {
            JSON.parse(msg);
            await processMessage(msg);
          } catch (e) {
            // Not valid JSON, keep in buffer
          }
        }
      }
      buffer = ''; // Clear buffer after processing
    }
    // Otherwise keep buffering
  }
});

// Handle process termination
process.on('SIGINT', () => {
  log('Bridge shutting down');
  process.exit(0);
});

process.on('uncaughtException', (error) => {
  log(`Uncaught error: ${error.message}`);
});

log(`Bridge started - connecting to ${SERVER_URL}`);