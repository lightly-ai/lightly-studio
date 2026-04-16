export type SavePendingChange =
    | boolean
    | {
          token: string;
          isPending: boolean;
      };
