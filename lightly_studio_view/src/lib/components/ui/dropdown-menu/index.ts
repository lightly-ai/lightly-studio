import { DropdownMenu as DropdownMenuPrimitive } from 'bits-ui';
import Content from './dropdown-menu-content.svelte';
import GroupHeading from './dropdown-menu-group-heading.svelte';
import Item from './dropdown-menu-item.svelte';
import Separator from './dropdown-menu-separator.svelte';

const Root = DropdownMenuPrimitive.Root;
const Trigger = DropdownMenuPrimitive.Trigger;
const Group = DropdownMenuPrimitive.Group;
const Portal = DropdownMenuPrimitive.Portal;

export {
    Root,
    Trigger,
    Group,
    Portal,
    Content,
    GroupHeading,
    Item,
    Separator,
    //
    Root as DropdownMenu,
    Trigger as DropdownMenuTrigger,
    Group as DropdownMenuGroup,
    Portal as DropdownMenuPortal,
    Content as DropdownMenuContent,
    GroupHeading as DropdownMenuGroupHeading,
    Item as DropdownMenuItem,
    Separator as DropdownMenuSeparator
};
