// Capacitor config — requires: npm install @capacitor/cli @capacitor/core
// import { CapacitorConfig } from '@capacitor/cli';

const config = {
  appId: 'co.ke.vestra',
  appName: 'Vestra',
  webDir: '.next/standalone',
  server: {
    androidScheme: 'https',
    cleartext: false,
  },
  plugins: {
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#0f172a',
      overlaysWebView: false,
    },
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#0f172a',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: true,
      spinnerColor: '#3b82f6',
    },
    Camera: {
      permissions: {
        camera: 'Vestra needs camera access to take property photos and document scans.',
        photos: 'Vestra needs photo library access to upload property images and ID documents.',
      },
    },
    Geolocation: {
      permissions: {
        location: 'Vestra uses your location to find nearby properties, calculate commute times, and provide accurate neighbourhood insights.',
      },
    },
  },
  ios: {
    contentInset: 'always',
    allowsLinkPreview: true,
    scrollEnabled: true,
  },
  android: {
    allowMixedContent: false,
    captureInput: true,
    useLegacyBridge: false,
  },
  cordova: {
    preferences: {
      DisableDeploy: 'true',
    },
  },
};

export default config;
