import { LayoutGrid } from 'lucide-react';

export type Platform = {
  name: string;
  href: string;
  logo: string;
};

export const platforms: Platform[] = [
  { name: 'Salesforce', href: '/platform/salesforce', logo: '/salesforce-logo.svg' },
  { name: 'Chargebee', href: '/platform/chargebee', logo: '/chargebee-logo.svg' },
  { name: 'Redshift', href: '/platform/redshift', logo: '/redshift-logo.svg' },
  { name: 'AWS', href: '/platform/aws', logo: '/aws-logo.svg' },
]; 