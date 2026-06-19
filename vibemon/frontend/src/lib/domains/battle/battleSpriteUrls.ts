const EMOTE_HAPPY_POSE = 'pose/emote-happy.png';

/** Map a battle pose asset URL to the matching happy emote pose. */
export function emoteHappyFromBattleSprite(spriteUrl: string | null | undefined): string | null {
	if (!spriteUrl) return null;
	const poseIndex = spriteUrl.indexOf('/pose/');
	if (poseIndex === -1) return null;
	const prefix = spriteUrl.slice(0, poseIndex + 1);
	return `${prefix}${EMOTE_HAPPY_POSE}`;
}
