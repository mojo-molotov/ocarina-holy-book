<script setup lang="ts">
import { computed } from 'vue';
import { useData, withBase } from 'vitepress';

const { site, frontmatter, lang } = useData();

const name = computed(() => frontmatter.value.blog?.name ?? site.value.title ?? '');
const motto = computed(() => frontmatter.value.blog?.motto ?? '');

const isFrench = computed(() => lang.value?.startsWith('fr'));
const pdfHref = computed(() => withBase(isFrench.value ? '/ocarina-fr.pdf' : '/ocarina-en.pdf'));
const pdfLabel = computed(() => (isFrench.value ? 'Télécharger (PDF)' : 'Download (PDF)'));
</script>

<template>
  <div>
    <h1>
      <span class="name">{{ name }}</span>
      <span v-show="motto" class="motto">{{ motto }}</span>
    </h1>
    <div class="download-wrapper">
      <a :href="pdfHref" :download="isFrench ? 'ocarina-fr.pdf' : 'ocarina-en.pdf'" class="download-button">
        {{ pdfLabel }}
      </a>
    </div>
  </div>
</template>

<style scoped>
h1 {
  text-align: center;
}
h1 .name {
  transition: all 0.25s ease-in-out 0.04s;
  transform: translateY(0px);
  opacity: 1;
  font-weight: bold;
  margin: 0 auto;
  font-size: 36px;
}
h1 .motto {
  position: relative;
  bottom: 0px;
  font-size: 14px;
  margin-left: 10px;
}
h1 .motto::before {
  content: '- ';
}

@media screen and (max-width: 500px) {
  .motto {
    display: none;
  }
}

.download-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  margin-bottom: 16px;
}
.download-button {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 8px;
  background-color: var(--vp-c-brand-1, #3eaf7c);
  color: #fff !important;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition:
    background-color 0.2s ease-in-out,
    transform 0.1s ease-in-out;
}
.download-button:hover {
  background-color: var(--vp-c-brand-2, #369870);
  transform: translateY(-1px);
}
.download-button:active {
  transform: translateY(0);
}
</style>
