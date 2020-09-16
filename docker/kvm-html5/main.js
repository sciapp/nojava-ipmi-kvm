"use strict";

const http = require('http'),
      connect = require('connect'),
      httpProxy = require('http-proxy'),
      transformerProxy = require('transformer-proxy'),
      cookie = require('cookie'),
      url = require('url');

const { execFileSync } = require('child_process');

// Read options and password
const fs = require('fs');
const config = JSON.parse(fs.readFileSync(0, 'utf-8'));

console.log("Config:", config);

// Check config:
if (!("kvm_password" in config && "kvm_host" in config)) {
  console.error("Error: Configuration is invalid.");
  process.exit(1);
}

// Execute get_java_viewer to acquire logged-in session
let get_java_viewer_args = process.argv.slice(2);
get_java_viewer_args.unshift("/usr/local/bin/get_java_viewer");
get_java_viewer_args.push('-S'); // force session_only call on get_java_viewer

let session_data = execFileSync("/usr/bin/python2", get_java_viewer_args, {
  input: config.kvm_password,
  encoding: 'utf-8',
  stdio: [null, 'pipe', 'inherit'], // disable info logging to session_data string
}).trim();
let session = JSON.parse(session_data)
console.log("Acquired session using get_java_viewer.");

// Define functions used multiple times


function checkAuthorization(req, socket) {
  if (!("authorization" in config)) {
    return true;
  }

  let cookies = req.headers['cookie'];
  if (cookies) {
    cookies = cookie.parse(cookies, {decode: (x) => x}); // Do not decode cookies using decodeURIComponent
    if (config.authorization.key in cookies && cookies[config.authorization.key] == config.authorization.value) {
      return true;
    }
  }

  // Authorization failed
  if (socket.writeHead) {
    socket.writeHead(401, {"Content-Type": "text/html", "Content-Length": 43});
    socket.end('You are not authorized to use this service.');
  } else {
    socket.end(`HTTP/1.1 401 Unauthorized
Content-Type: text/html
Content-Length: 43

You are not authorized to use this service.`
    );
  }
  return false;
}

// This function replaces/inserts all cookies from the session into the cookieStr and returns the modified string
function updateCookieString(cookieStr) {
  // parse cookiestring without decoding of url components into a dictionary
  let cookies = cookie.parse(cookieStr, {decode: (x) => x});

  // Overwrite cookies with session cookies
  cookies = Object.assign(cookies, session.cookies);

  // Convert them back without actually encoding strings.
  return Object.entries(cookies).map((entry) => cookie.serialize(entry[0], entry[1], {encode: (x) => x})).join('; ');
}

const PROXY_TO = config.kvm_host;
const PROXY_PORT = 8080;


console.log(`Starting proxy on ${PROXY_PORT}`);
var app = connect(); // connect is a stack of handler functions
var proxy = new httpProxy.createProxyServer({
  target: PROXY_TO,
  preserveHeaderKeyCase: true,
  changeOrigin: true,
  secure: false,
});

if ("rewrites" in config) {
  // Insert a transformerproxy for each rewrite in config
  config.rewrites.forEach((rewrite) => {
    let matchRegex = RegExp(rewrite.search);
    let pathRegex = RegExp(rewrite.path_match);
    console.log("Inserting replacer: (path:", pathRegex, ") match:", matchRegex, "replace:", rewrite.replace);

    app.use(transformerProxy((data, req, res) => {
      console.log("Rewrote request to", req.url);
      return Buffer.from(data.toString('utf8').replace(matchRegex, rewrite.replace), 'utf8');
    }, {match: pathRegex}));
  })
}

// Proxy normal requests
app.use(function (req, res) {
  // if authorization is failed, request is sent a 401
  if (!checkAuthorization(req, res)) {
    return;
  }

  // Find Cookie Header in raw Headers or create a new one
  let cookieIdx = -1;
  for (let i = 0; i < req.rawHeaders.length; i += 2) {
    if (req.rawHeaders[i].toLowerCase() == 'cookie') {
      cookieIdx = i + 1;
      break;
    }
  }

  // if cookie header was not found, create one
  if (cookieIdx === -1) {
    cookieIdx = req.rawHeaders.length + 1;
    req.rawHeaders.push('Cookie');
    req.rawHeaders.push('');
  }

  // Add session to request
  req.rawHeaders[cookieIdx] = updateCookieString(req.rawHeaders[cookieIdx]);

  let refererIdx = -1;
  for (let i = 0; i < req.rawHeaders.length; i += 2) {
    if (req.rawHeaders[i].toLowerCase() == 'referer') {
      refererIdx = i + 1;
      break;
    }
  }

  if (refererIdx != -1) {
    let currUrl = new url.URL(req.rawHeaders[refererIdx]);
    let newUrl = new url.URL(PROXY_TO);
    currUrl.protocol = newUrl.protocol;
    currUrl.hostname = newUrl.hostname;
    currUrl.port = newUrl.port;
    currUrl.auth = newUrl.auth;
    req.rawHeaders[refererIdx] = currUrl.href;
  }


  // pass the request
  proxy.web(req, res);
});

// Create HTTP server to serve proxy
var proxyServer = http.createServer(app);

//
// Listen to the `upgrade` event and proxy the
// WebSocket requests as well.
//
proxyServer.on('upgrade', function (req, socket, head) {
  // if authorization is failed, request is sent a 401
  if (checkAuthorization(req, socket)) {
    proxy.ws(req, socket, head);
  }
});

// It is easier to set the headers for websockets in this events, as req does not contain modifieable headers
proxy.on('proxyReqWs', (proxyReq, req, socket, options, head) => {
  proxyReq.setHeader("Cookie", updateCookieString(proxyReq.getHeader("Cookie") || ""));

  let referer = proxyReq.getHeader("Referer");
  if (referer) {
    let currUrl = new url.URL(referer);
    let newUrl = new url.URL(PROXY_TO);
    currUrl.protocol = newUrl.protocol;
    currUrl.hostname = newUrl.hostname;
    currUrl.port = newUrl.port;
    currUrl.auth = newUrl.auth;
    proxyReq.setHeader("Referer", currUrl.href);
  }
});

// Basic error logging
proxy.on('error', function (e,req){
  if(e){
    console.error(e.message);
    console.log(req.headers.host,'-->',PROXY_TO);
    console.log('-----');
  }
});

proxyServer.listen(PROXY_PORT);

console.log("Proxy is listening");
