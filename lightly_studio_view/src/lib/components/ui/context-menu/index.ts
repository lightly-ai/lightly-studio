import { ContextMenu as ContextMenuPrimitive } from "bits-ui";

import Content from "./context-menu-content.svelte";
import GroupHeading from "./context-menu-group-heading.svelte";
import Item from "./context-menu-item.svelte";
import Separator from "./context-menu-separator.svelte";
import SubContent from "./context-menu-sub-content.svelte";
import SubTrigger from "./context-menu-sub-trigger.svelte";

const Root = ContextMenuPrimitive.Root;
const Trigger = ContextMenuPrimitive.Trigger;
const Group = ContextMenuPrimitive.Group;
const Sub = ContextMenuPrimitive.Sub;

export {
	Root,
	Trigger,
	Content,
	Item,
	Group,
	GroupHeading,
	Separator,
	Sub,
	SubContent,
	SubTrigger,
	//
	Root as ContextMenu,
	Trigger as ContextMenuTrigger,
	Content as ContextMenuContent,
	Item as ContextMenuItem,
	Group as ContextMenuGroup,
	GroupHeading as ContextMenuGroupHeading,
	Separator as ContextMenuSeparator,
	Sub as ContextMenuSub,
	SubContent as ContextMenuSubContent,
	SubTrigger as ContextMenuSubTrigger,
};
