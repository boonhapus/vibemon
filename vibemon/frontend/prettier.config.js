/** @type {import('prettier').Config} */
export default {
	plugins: ['@ianvs/prettier-plugin-sort-imports', 'prettier-plugin-svelte'],
	overrides: [{ files: '*.svelte', options: { parser: 'svelte' } }],
	useTabs: true,
	singleQuote: true,
	trailingComma: 'none',
	printWidth: 120,
	importOrder: ['<BUILTIN_MODULES>', '', '<THIRD_PARTY_MODULES>', '', '^\\$lib/', '', '^[./]'],
	importOrderParserPlugins: ['typescript'],
	importOrderTypeScriptVersion: '5.0.0'
};
