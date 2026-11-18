import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ElAlert,
  ElAvatar,
  ElButton,
  ElButtonGroup,
  ElCard,
  ElCheckbox,
  ElDatePicker,
  ElDialog,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLoadingDirective,
  ElMessageBox,
  ElOption,
  ElOptionGroup,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSkeleton,
  ElSwitch,
  ElTag,
  ElTimePicker,
  provideGlobalConfig
} from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import './styles/themes.css'
import './styles/base.css'
import './styles/redesign.css'

const app = createApp(App).use(createPinia())
const components = [
  ElAlert, ElAvatar, ElButton, ElButtonGroup, ElCard, ElCheckbox, ElDatePicker,
  ElDialog, ElDivider, ElEmpty, ElForm, ElFormItem, ElIcon, ElInput,
  ElInputNumber, ElOption, ElOptionGroup, ElRadioButton, ElRadioGroup, ElSelect, ElSkeleton,
  ElSwitch, ElTag, ElTimePicker
]

components.forEach((component) => app.component(component.name!, component))
app.directive('loading', ElLoadingDirective)
provideGlobalConfig({ locale: zhCn }, app, true)
app.mount('#app')
