import argparse
import typing

import pydantic


class Pack(pydantic.BaseModel):
    network: str = pydantic.Field(
        regex="(?=^.{1,254}$)(^(?:(?!\d+\.|-)[a-zA-Z0-9_\-]{1,63}(?<!-)\.?)+(?:[a-zA-Z]{2,})$)"
    )
    channels: typing.List[str] = pydantic.Field(min_length=1)
    peer: str = pydantic.Field(min_length=1)
    number: int = pydantic.Field(gt=0)

    @pydantic.validator("channels", pre=True)
    def required_channels(cls, value: str) -> typing.List[str]:
        if isinstance(value, str):
            return value.split(",")

        return value

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        return cls(
            network=args.network,
            channels=args.channels,
            peer=args.bot,
            number=args.pack_num,
        )
