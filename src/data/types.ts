export type Link = { label: string; href: string };

export type Author = {
  name: string;
  equal?: boolean;
  corresponding?: boolean;
};

export type Publication = {
  id: string;
  kind: 'journal' | 'conference';
  role: 'first' | 'coauthor';
  year: string;
  title: string;
  venue: string;
  authors: Author[];
  href: string;
  doi?: string;
  detail?: string;
};

export type Talk = {
  id: string;
  role: 'oral' | 'poster' | 'coauthor';
  title: string;
  event: string;
  date: string;
  youtubeId?: string;
};

export type Video = {
  youtubeId: string;
  title: string;
  detail: string;
};

export type ResearchCard = {
  id: string;
  kicker: string;
  title: string;
  body: string;
  tags: string[];
  links: Link[];
};

export type ResearchPeriod = {
  id: string;
  when: string;
  where: string;
  points: string[];
};

export type Beamtime = {
  title: string;
  doi: string;
  date: string;
};

export type TimelineItem = {
  id: string;
  kind: 'education' | 'employment' | 'teaching' | 'service';
  dates: string;
  place: string;
  title: string;
  org: string;
  orgUrl?: string;
  points: string[];
};

export type Award = {
  title: string;
  meta: string;
  detail?: string;
};

export type SkillGroup = {
  title: string;
  items: string[];
};

export type Fact = {
  value: string;
  label: string;
  href?: string;
};

export type SiteContent = {
  lang: 'en' | 'ko';
  home: string;
  meta: { title: string; description: string };
  nav: { href: string; label: string }[];
  ui: {
    skip: string;
    themeToLight: string;
    themeToDark: string;
    language: string;
    downloadCv: string;
    cvPdf: string;
    cvDocx: string;
    all: string;
    journal: string;
    conference: string;
    presenting: string;
    coauthor: string;
    article: string;
    doi: string;
    play: string;
    equal: string;
    corresponding: string;
    role: Record<'first' | 'coauthor' | 'oral' | 'poster', string>;
    kind: Record<'education' | 'employment' | 'teaching' | 'service', string>;
    keywords: string;
    beamtimeLabel: string;
    labApproaches: string;
    labAttribution: string;
    pastLabAttribution: string;
    scholarCta: string;
    talksFilters: string;
    pubFilters: string;
    external: string;
  };
  hero: {
    eyebrow: string;
    name: string;
    altName: string;
    role: string;
    lede: string;
    affiliation: string;
    affiliationHref: string;
    pi: string;
    piHref: string;
    facts: Fact[];
    links: Link[];
  };
  about: {
    title: string;
    dek: string;
    paragraphs: string[];
  };
  media: {
    portraitAlt: string;
    portraitCaption: string;
    campusAlt: string;
    campusCaption: string;
    labAlt: string;
    labCaption: string;
    overviewAlt: string;
    overviewCaption: string;
    spallationAlt: string;
    spallationCaption: string;
    lmdAlt: string;
    lmdCaption: string;
  };
  research: {
    title: string;
    dek: string;
    keywords: string[];
    cards: ResearchCard[];
    experienceTitle: string;
    experienceDek: string;
    periods: ResearchPeriod[];
    beamtimeTitle: string;
    beamtimeDek: string;
    beamtimes: Beamtime[];
    projectsTitle: string;
    projectsDek: string;
    projects: string[];
  };
  lab: {
    name: string;
    pi: string;
    place: string;
    url: string;
    urlLabel: string;
    summary: string;
    approaches: string[];
  };
  pastLab: {
    name: string;
    pi: string;
    place: string;
    url: string;
    urlLabel: string;
    summary: string;
  };
  publications: {
    title: string;
    dek: string;
    items: Publication[];
  };
  talks: {
    title: string;
    dek: string;
    items: Talk[];
    videosTitle: string;
    videosDek: string;
    videos: Video[];
  };
  awards: {
    title: string;
    dek: string;
    fellowship: Award;
    scholarshipsTitle: string;
    scholarships: Award[];
    awardsTitle: string;
    items: Award[];
    activitiesTitle: string;
    activities: string[];
  };
  timeline: {
    title: string;
    dek: string;
    items: TimelineItem[];
  };
  skills: {
    title: string;
    dek: string;
    groups: SkillGroup[];
  };
  contact: {
    title: string;
    dek: string;
    paragraphs: string[];
    cvNote: string;
    links: Link[];
  };
  footer: string;
};
