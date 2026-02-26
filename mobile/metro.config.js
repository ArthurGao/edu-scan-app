const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

// Enable "exports" support for modern packages like axios 1.x
config.resolver.unstable_enablePackageExports = true;

// Prioritize react-native specific entry points
config.resolver.resolverMainFields = ['react-native', 'browser', 'main'];

// Shim Node-only modules to an empty object
config.resolver.extraNodeModules = {
    crypto: path.resolve(__dirname, 'src/shims/empty.ts'),
    stream: path.resolve(__dirname, 'src/shims/empty.ts'),
    url: path.resolve(__dirname, 'src/shims/empty.ts'),
    buffer: path.resolve(__dirname, 'src/shims/empty.ts'),
};

module.exports = config;
