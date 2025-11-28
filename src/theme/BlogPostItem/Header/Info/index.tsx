import React, {type ReactNode} from 'react';
import Info from '@theme-original/BlogPostItem/Header/Info';
import type InfoType from '@theme/BlogPostItem/Header/Info';
import type {WrapperProps} from '@docusaurus/types';

type Props = WrapperProps<typeof InfoType>;

export default function InfoWrapper(props: Props): ReactNode {
  return (
    <>
      <Info {...props} />
    </>
  );
}
