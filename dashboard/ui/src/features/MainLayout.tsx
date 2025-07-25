import type { FC } from "react";
import { NavbarDemo } from "@/features/NavbarDemo";
import { RequestDemo } from "@/features/RequestDemo";

export const MainLayout: FC = () => {

  return (<>
    <div>Sample text</div>
    <RequestDemo/>
    <NavbarDemo/>
  </>);

};
