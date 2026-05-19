<script setup lang="ts">
import { useData } from 'vitepress';
import { computed } from 'vue';

const { lang } = useData();

const i18n = computed(
  () =>
    ({
      fr: {
        code: '404',
        title: 'PAGE INTROUVABLE',
        quote: "Cette page n'existe pas ou a été déplacée.",
        linkLabel: "retour à l'accueil",
        linkText: "Retour à l'accueil",
        link: '/fr/'
      },
      en: {
        code: '404',
        title: 'PAGE NOT FOUND',
        quote: "The page you're looking for doesn't exist.",
        linkLabel: 'go to home',
        linkText: 'Take me home',
        link: '/'
      },
      ru: {
        code: '404',
        title: 'СТРАНИЦА НЕ НАЙДЕНА',
        quote: 'Страница, которую вы ищете, не существует.',
        linkLabel: 'перейти на главную',
        linkText: 'На главную',
        link: '/'
      }
    })[lang.value] ?? {
      code: '404',
      title: 'PAGE NOT FOUND',
      quote: '',
      linkLabel: 'go to home',
      linkText: 'Home',
      link: '/'
    }
);
</script>

<template>
  <div class="NotFound">
    <p class="code">{{ i18n.code }}</p>
    <h1 class="title">{{ i18n.title }}</h1>
    <div class="divider" />
    <blockquote class="quote">{{ i18n.quote }}</blockquote>
    <div class="action">
      <a class="link" :href="i18n.link" :aria-label="i18n.linkLabel">
        {{ i18n.linkText }}
      </a>
    </div>
  </div>
</template>

<style>
.NotFound {
  min-height: calc(100vh - var(--vp-nav-height));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.NotFound .code {
  line-height: 64px;
  font-size: 64px;
  font-weight: 600;
}

.NotFound .title {
  padding-top: 12px;
  letter-spacing: 2px;
  line-height: 20px;
  font-size: 20px;
  font-weight: 700;
}

.NotFound .divider {
  margin: 24px auto 18px;
  width: 64px;
  height: 1px;
  background-color: var(--vp-c-divider);
}

.NotFound .quote {
  margin: 0 auto;
  max-width: 512px;
  font-size: 14px;
  font-weight: 500;
  color: var(--vp-c-text-2);
}

.NotFound .action {
  padding-top: 20px;
}

.NotFound .link {
  display: inline-block;
  border: 1px solid var(--vp-c-brand-1);
  border-radius: 16px;
  padding: 3px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--vp-c-brand-1);
  transition:
    border-color 0.25s,
    color 0.25s;
}

.NotFound .link:hover {
  border-color: var(--vp-c-brand-2);
  color: var(--vp-c-brand-2);
}
</style>
