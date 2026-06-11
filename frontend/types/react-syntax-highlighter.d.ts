declare module 'react-syntax-highlighter' {
  import { ComponentType } from 'react';
  export const Prism: ComponentType<any>;
  export const Light: ComponentType<any>;
}

declare module 'react-syntax-highlighter/dist/esm/styles/prism' {
  export const oneDark: any;
  export const oneLight: any;
}
