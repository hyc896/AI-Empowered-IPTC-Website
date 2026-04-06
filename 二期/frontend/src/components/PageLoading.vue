<template>
  <div class="page-loading-wrapper">
    <div class="loader"></div>
  </div>
</template>

<style scoped>
.page-loading-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  width: 100%;
}
.loader {
  width: fit-content;
  font-size: 40px;
  font-family: monospace;
  font-weight: bold;
  text-transform: uppercase;
  color: #0000;
  -webkit-text-stroke: 1px #000;
  background: linear-gradient(90deg, #0000 33%, #000 0 67%, #0000 0) 100%/300%
    100% no-repeat text;
  animation: l12 4s steps(14) infinite;
}
.loader:before {
  content: "Loading";
}
@keyframes l12 {
  to {
    background-position: 0;
  }
}
</style>
